import inspect
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)
from uuid import UUID

from pydantic import BaseModel
from starlette.routing import BaseRoute, Route
from starlette.schemas import SchemaGenerator

from .dependencies import Depends
from .filters import OrderingFilter, QueryParameterFilterBackend, SearchFilter
from .serializers import BooleanField as NzrBooleanField
from .serializers import CharField as NzrCharField
from .serializers import DateTimeField as NzrDateTimeField
from .serializers import DictField as NzrDictField
from .serializers import Field as NzrField
from .serializers import IntegerField as NzrIntegerField
from .serializers import ListField as NzrListField
from .typing import Body, PathParam, QueryParam


class NzrApiSchemaGenerator(SchemaGenerator):
    """Enhanced schema generator with automatic documentation generation."""

    def __init__(self, info: Dict[str, Any]):
        base_schema = {"openapi": "3.0.3", "info": info}
        super().__init__(base_schema)
        self.info = info
        self.components_schemas: Dict[str, Any] = {}

    def get_schema(self, routes: Sequence[BaseRoute]) -> Dict[str, Any]:
        """Generate comprehensive OpenAPI 3.0 schema."""
        paths: Dict[str, Dict[str, Any]] = {}

        for route in routes:
            if not isinstance(route, Route):
                continue

            if route.include_in_schema is False:
                continue

            path = route.path
            openapi_path = path.replace("{", "{").replace("}", "}")

            if openapi_path not in paths:
                paths[openapi_path] = {}

            for method in route.methods:
                method_lower = method.lower()
                if method_lower == "head":
                    continue

                operation = self.get_operation_for_route(route, method)
                if operation:
                    paths[openapi_path][method_lower] = operation

        schema: Dict[str, Any] = {
            "openapi": "3.0.3",
            "info": self.info,
            "paths": paths,
        }

        # Add components section
        if self.components_schemas:
            if "components" not in schema:
                schema["components"] = {}
            schema["components"]["schemas"] = self.components_schemas

        # Detect and add security schemes from routes
        security_schemes = self._extract_security_schemes(routes)
        if security_schemes:
            if "components" not in schema:
                schema["components"] = {}
            schema["components"]["securitySchemes"] = security_schemes

        return schema

    def get_operation_for_route(self, route: Route, method: str) -> Optional[Dict[str, Any]]:
        """Generate OpenAPI operation for route with advanced type introspection."""

        # Get the original function (unwrapped from decorators)
        endpoint_func = getattr(route.endpoint, "_original_func", route.endpoint)

        if not callable(endpoint_func):
            return None

        operation: Dict[str, Any] = {"responses": {"200": {"description": "Successful Response"}}}
        method_lower = method.lower()

        # Get function signature and type hints
        signature = inspect.signature(endpoint_func)
        type_hints = get_type_hints(endpoint_func)

        # Extract summary and description from docstring
        if endpoint_func.__doc__:
            docstring_lines = endpoint_func.__doc__.strip().split("\n")
            operation["summary"] = docstring_lines[0].strip()
            if len(docstring_lines) > 1:
                operation["description"] = "\n".join(docstring_lines[1:]).strip()

        # Generate parameters from function signature
        parameters: List[Dict[str, Any]] = []
        request_body: Optional[Dict[str, Any]] = None

        for param_name, param in signature.parameters.items():
            # Skip self and request parameters
            if param_name in ("self", "request"):
                continue

            annotation = type_hints.get(param_name, param.annotation)

            # Handle path parameters
            if param_name in self._extract_path_params(route.path):
                param_schema = self._get_parameter_schema(param_name, annotation, param.default, "path")
                if param_schema:
                    parameters.append(param_schema)
                continue

            # Handle query parameters with Query annotation
            if param.default and isinstance(param.default, QueryParam):
                param_schema = self._get_query_parameter_schema(param_name, annotation, param.default)
                if param_schema:
                    parameters.append(param_schema)
                continue

            # Handle request body (Pydantic models)
            if self._is_body_parameter(annotation):
                request_body = self._generate_request_body_schema(annotation)
                continue

        if parameters:
            operation["parameters"] = parameters

        # If this is a class-based view, prefer serializer-driven schema generation
        view_class = getattr(route.endpoint, "view_class", None)
        if view_class is not None:
            serializer_request, serializer_response, is_list = self._get_serializers_for_view_method(
                view_class, method_lower, route
            )

            # Build request body from serializer
            if serializer_request is not None:
                operation["requestBody"] = self._generate_request_body_schema_from_serializer(serializer_request)

            # Build response schema from serializer
            if serializer_response is not None:
                status_code = (
                    "201" if method_lower == "post" else ("200" if method_lower in {"get", "put", "patch"} else "204")
                )
                if status_code != "204":
                    if method_lower == "get" and is_list:
                        operation["responses"][status_code] = self._generate_list_response_schema_from_serializer(
                            serializer_response
                        )
                    else:
                        operation["responses"][status_code] = self._generate_response_schema_from_serializer(
                            serializer_response
                        )
                else:
                    operation["responses"][status_code] = {"description": "No Content"}
        else:
            # Fallback to type-hint based request body if available
            if request_body:
                operation["requestBody"] = request_body

        # Handle response model (function-based routes with Pydantic models)
        response_model = getattr(route.endpoint, "_response_model", None)
        if response_model:
            operation["responses"]["200"] = self._generate_response_schema(response_model)

        # Check for custom docs provided by the @docs decorator
        if hasattr(route.endpoint, "_openapi_docs"):
            custom_docs = route.endpoint._openapi_docs
            for key, value in custom_docs.items():
                if value is not None:
                    operation[key] = value

        # Auto-generate parameters for pagination and filtering (legacy support)
        if hasattr(route.endpoint, "view_class") and method.lower() == "get":
            view_class = route.endpoint.view_class
            self._add_pagination_params(operation, view_class)
            self._add_filter_params(operation, view_class)
            self._add_ordering_params(operation, view_class)
            self._add_search_params(operation, view_class)

        return operation

    # --- Serializer-based schema helpers ---

    def _get_serializers_for_view_method(
        self, view_class: Type[Any], method_lower: str, route: Route
    ) -> Tuple[Optional[Type[Any]], Optional[Type[Any]], bool]:
        """Infer request and response serializers from a class-based view and HTTP method.

        Returns: (request_serializer_cls, response_serializer_cls, is_list: bool)
        """
        # Defaults
        req_ser = getattr(view_class, "serializer_class", None)
        resp_ser = getattr(view_class, "response_serializer", None) or getattr(view_class, "serializer_class", None)

        is_list = False

        if method_lower == "get":
            # Determine list vs retrieve by presence of path parameters in the route path
            path_has_params = bool(self._extract_path_params(route.path))
            is_list = not path_has_params
            # GET has no request body
            req_ser = None
        elif method_lower == "post":
            # Create: request uses serializer_class, response prefers response_serializer
            pass
        elif method_lower in {"put", "patch"}:
            # Update: request uses serializer_class, response prefers response_serializer
            pass
        elif method_lower == "delete":
            req_ser = None
            resp_ser = None

        return req_ser, resp_ser, is_list

    def _generate_request_body_schema_from_serializer(self, serializer_cls: Type[Any]) -> Dict[str, Any]:
        schema_ref = self._serializer_to_schema_ref(serializer_cls, request=True)
        return {"required": True, "content": {"application/json": {"schema": {"$ref": schema_ref}}}}

    def _generate_response_schema_from_serializer(self, serializer_cls: Type[Any]) -> Dict[str, Any]:
        schema_ref = self._serializer_to_schema_ref(serializer_cls, request=False)
        return {"description": "Successful Response", "content": {"application/json": {"schema": {"$ref": schema_ref}}}}

    def _generate_list_response_schema_from_serializer(self, serializer_cls: Type[Any]) -> Dict[str, Any]:
        item_ref = self._serializer_to_schema_ref(serializer_cls, request=False)
        schema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
                "page": {"type": "integer"},
                "limit": {"type": "integer"},
                "results": {"type": "array", "items": {"$ref": item_ref}},
            },
        }
        return {"description": "Successful Response", "content": {"application/json": {"schema": schema}}}

    def _serializer_to_schema_ref(self, serializer_cls: Type[Any], request: bool) -> str:
        name = serializer_cls.__name__ + ("Request" if request else "Response")
        if name not in self.components_schemas:
            self.components_schemas[name] = self._serializer_to_schema(serializer_cls, request=request)
        return f"#/components/schemas/{name}"

    def _serializer_to_schema(self, serializer_cls: Type[Any], request: bool) -> Dict[str, Any]:
        """Convert a NzrApi serializer into an OpenAPI schema object.

        request=True -> include only writable fields; mark required appropriately.
        request=False -> include readable fields; mark writeOnly appropriately.
        """
        try:
            serializer = serializer_cls()
        except Exception:
            # Fallback to an empty object if instantiation fails
            return {"type": "object"}

        properties: Dict[str, Any] = {}
        required: List[str] = []

        fields: Dict[str, NzrField] = getattr(serializer, "fields", {})
        for name, field in fields.items():
            # Filter by read/write for request/response
            if request and getattr(field, "read_only", False):
                continue
            if not request and getattr(field, "write_only", False):
                continue

            prop_schema = self._nzr_field_to_schema(field)
            if getattr(field, "read_only", False):
                prop_schema["readOnly"] = True
            if getattr(field, "write_only", False):
                prop_schema["writeOnly"] = True

            properties[name] = prop_schema

            if request and getattr(field, "required", False) and not getattr(field, "read_only", False):
                required.append(name)

        schema: Dict[str, Any] = {"type": "object", "properties": properties}
        if request and required:
            schema["required"] = required
        return schema

    def _nzr_field_to_schema(self, field: NzrField) -> Dict[str, Any]:
        """Map NzrApi Field to OpenAPI schema."""
        if isinstance(field, NzrCharField):
            schema: Dict[str, Any] = {"type": "string"}
            if getattr(field, "max_length", None):
                schema["maxLength"] = field.max_length
            return schema
        if isinstance(field, NzrIntegerField):
            return {"type": "integer"}
        if isinstance(field, NzrBooleanField):
            return {"type": "boolean"}
        if isinstance(field, NzrDateTimeField):
            return {"type": "string", "format": "date-time"}
        if isinstance(field, NzrDictField):
            return {"type": "object"}
        if isinstance(field, NzrListField):
            try:
                item_schema = self._nzr_field_to_schema(field.child)
            except Exception:
                item_schema = {"type": "string"}
            return {"type": "array", "items": item_schema}

        # Default fallback
        return {"type": "string"}

    def _add_pagination_params(self, operation: Dict[str, Any], view_class: Any):
        if not hasattr(view_class, "pagination_class") or not view_class.pagination_class:
            return

        if "parameters" not in operation:
            operation["parameters"] = []

        operation["parameters"].extend(
            [
                {
                    "name": "page",
                    "in": "query",
                    "required": False,
                    "description": "A page number within the paginated result set.",
                    "schema": {"type": "integer", "default": 1},
                },
                {
                    "name": "limit",
                    "in": "query",
                    "required": False,
                    "description": "Number of results to return per page.",
                    "schema": {"type": "integer"},
                },
            ]
        )

    def _add_filter_params(self, operation: Dict[str, Any], view_class: Any):
        filter_backends = getattr(view_class, "filter_backends", [])
        filterset_fields = getattr(view_class, "filterset_fields", [])

        if not any(isinstance(b(), QueryParameterFilterBackend) for b in filter_backends) or not filterset_fields:
            return

        if "parameters" not in operation:
            operation["parameters"] = []

        for field in filterset_fields:
            operation["parameters"].append(
                {
                    "name": field,
                    "in": "query",
                    "required": False,
                    "description": f"Filter by {field}",
                    "schema": {"type": "string"},
                }
            )

    def _add_ordering_params(self, operation: Dict[str, Any], view_class: Any):
        filter_backends = getattr(view_class, "filter_backends", [])
        ordering_fields = getattr(view_class, "ordering_fields", [])

        if not any(issubclass(b, OrderingFilter) for b in filter_backends) or not ordering_fields:
            return

        if "parameters" not in operation:
            operation["parameters"] = []

        description = f"Order by fields: {', '.join(ordering_fields)}. Prepend '-' for descending order."

        operation["parameters"].append(
            {
                "name": "ordering",
                "in": "query",
                "required": False,
                "description": description,
                "schema": {"type": "string"},
            }
        )

    def _add_search_params(self, operation: Dict[str, Any], view_class: Any):
        filter_backends = getattr(view_class, "filter_backends", [])
        search_fields = getattr(view_class, "search_fields", [])

        if not any(issubclass(b, SearchFilter) for b in filter_backends) or not search_fields:
            return

        if "parameters" not in operation:
            operation["parameters"] = []

        search_param = getattr(SearchFilter, "search_param", "search")
        description = f"A search term to search across fields: {', '.join(search_fields)}."

        operation["parameters"].append(
            {
                "name": search_param,
                "in": "query",
                "required": False,
                "description": description,
                "schema": {"type": "string"},
            }
        )

    def _extract_path_params(self, path: str) -> List[str]:
        """Extract path parameter names from route path."""
        import re

        return re.findall(r"\{(\w+)\}", path)

    def _get_parameter_schema(
        self, param_name: str, annotation: Type, default: Any, param_in: str
    ) -> Optional[Dict[str, Any]]:
        """Generate parameter schema for OpenAPI."""

        schema = self._type_to_openapi_schema(annotation)
        if not schema:
            return None

        param_schema: Dict[str, Any] = {"name": param_name, "in": param_in, "schema": schema}

        # Handle path parameters (always required)
        if param_in == "path":
            param_schema["required"] = True
        else:
            param_schema["required"] = default == inspect.Parameter.empty

        if isinstance(default, (PathParam, QueryParam)):
            if default.description:
                param_schema["description"] = default.description
            if default.example is not None:
                param_schema["example"] = default.example
            if default.deprecated:
                param_schema["deprecated"] = True

        return param_schema

    def _get_query_parameter_schema(
        self, param_name: str, annotation: Type, query_param: QueryParam
    ) -> Optional[Dict[str, Any]]:
        """Generate query parameter schema."""

        schema = self._type_to_openapi_schema(annotation)
        if not schema:
            return None

        param_schema: Dict[str, Any] = {
            "name": param_name,
            "in": "query",
            "schema": schema,
            "required": query_param.default == ...,
        }

        if query_param.description:
            param_schema["description"] = query_param.description
        if query_param.example is not None:
            param_schema["example"] = query_param.example
        if query_param.deprecated:
            param_schema["deprecated"] = True
        if query_param.default != ... and query_param.default is not None:
            param_schema["schema"]["default"] = query_param.default

        return param_schema

    def _is_body_parameter(self, annotation: Type) -> bool:
        """Check if parameter should be treated as request body."""
        if annotation == inspect.Parameter.empty:
            return False

        # Check if it's a Pydantic model
        try:
            return inspect.isclass(annotation) and issubclass(annotation, BaseModel)
        except TypeError:
            return False

    def _generate_request_body_schema(self, model_class: Type[BaseModel]) -> Dict[str, Any]:
        """Generate request body schema from Pydantic model."""
        schema_ref = self._model_to_schema_ref(model_class)

        return {"required": True, "content": {"application/json": {"schema": {"$ref": schema_ref}}}}

    def _generate_response_schema(self, model_class: Type[BaseModel]) -> Dict[str, Any]:
        """Generate response schema from Pydantic model."""
        schema_ref = self._model_to_schema_ref(model_class)

        return {"description": "Successful Response", "content": {"application/json": {"schema": {"$ref": schema_ref}}}}

    def _model_to_schema_ref(self, model_class: Type[BaseModel]) -> str:
        """Convert Pydantic model to schema reference."""
        schema_name = model_class.__name__

        # Generate the schema if not already present
        if schema_name not in self.components_schemas:
            self.components_schemas[schema_name] = model_class.schema()

        return f"#/components/schemas/{schema_name}"

    def _type_to_openapi_schema(self, python_type: Type) -> Optional[Dict[str, Any]]:
        """Convert Python type to OpenAPI schema."""
        if python_type == inspect.Parameter.empty:
            return {"type": "string"}

        origin = get_origin(python_type)
        args = get_args(python_type)

        # Handle Optional types
        if origin is Union and len(args) == 2 and type(None) in args:
            inner_type = args[0] if args[1] is type(None) else args[1]
            schema = self._type_to_openapi_schema(inner_type)
            if schema:
                schema["nullable"] = True
            return schema

        # Handle List types
        if origin is list or origin is List:
            item_type = args[0] if args else Any
            item_schema = self._type_to_openapi_schema(item_type)
            return {"type": "array", "items": item_schema or {"type": "string"}}

        # Handle Dict types
        if origin is dict or origin is Dict:
            return {"type": "object"}

        # Basic types
        if python_type == str:
            return {"type": "string"}
        elif python_type == int:
            return {"type": "integer"}
        elif python_type == float:
            return {"type": "number"}
        elif python_type == bool:
            return {"type": "boolean"}
        elif python_type == datetime:
            return {"type": "string", "format": "date-time"}
        elif python_type == UUID:
            return {"type": "string", "format": "uuid"}
        elif python_type and hasattr(python_type, "__bases__") and issubclass(python_type, Enum):
            return {"type": "string", "enum": [item.value for item in python_type]}
        elif python_type and hasattr(python_type, "__bases__") and issubclass(python_type, BaseModel):
            return {"$ref": self._model_to_schema_ref(python_type)}

        # Default to string for unknown types
        return {"type": "string"}

    def _extract_security_schemes(self, routes: Sequence[BaseRoute]) -> Dict[str, Any]:
        """Extract security schemes from route dependencies"""
        schemes = {}

        for route in routes:
            if not isinstance(route, Route):
                continue

            # Get the original function
            endpoint_func = getattr(route.endpoint, "_original_func", route.endpoint)
            if not callable(endpoint_func):
                continue

            # Check function signature for security dependencies
            signature = inspect.signature(endpoint_func)
            for param_name, param in signature.parameters.items():
                if isinstance(param.default, Depends):
                    security_scheme = self._get_security_scheme_from_dependency(param.default.dependency)
                    if security_scheme:
                        scheme_name = self._get_scheme_name(param.default.dependency)
                        schemes[scheme_name] = security_scheme

        return schemes

    def _get_security_scheme_from_dependency(self, dependency_func: Callable) -> Optional[Dict[str, Any]]:
        """Extract OpenAPI security scheme from dependency function"""

        # Check if it's a security scheme instance
        if hasattr(dependency_func, "get_openapi_security_scheme"):
            return dependency_func.get_openapi_security_scheme()

        # Check common security dependency patterns
        func_name = getattr(dependency_func, "__name__", "")

        if "basic" in func_name.lower():
            return {"type": "http", "scheme": "basic", "description": "HTTP Basic Authentication"}
        elif "bearer" in func_name.lower() or "jwt" in func_name.lower():
            return {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Bearer token authentication",
            }
        elif "api_key" in func_name.lower() or "apikey" in func_name.lower():
            return {"type": "apiKey", "name": "X-API-Key", "in": "header", "description": "API Key authentication"}
        elif "oauth2" in func_name.lower():
            return {
                "type": "oauth2",
                "flows": {"password": {"tokenUrl": "/token"}},
                "description": "OAuth2 authentication",
            }

        return None

    def _get_scheme_name(self, dependency_func: Callable) -> str:
        """Generate scheme name from dependency function"""
        if hasattr(dependency_func, "scheme_name") and dependency_func.scheme_name:
            return dependency_func.scheme_name

        func_name = getattr(dependency_func, "__name__", "unknown")
        return func_name.replace("get_current_user_", "").replace("_auth", "").replace("_", "")
