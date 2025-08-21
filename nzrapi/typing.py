"""
Advanced type system for NzrApi framework with automatic validation
Integrated with nzrapi's architecture for robust type safety
"""

import inspect
import json
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Type, Union, get_args, get_origin, get_type_hints
from uuid import UUID

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError
from starlette.requests import Request as StarletteRequest

from .exceptions import ValidationError
from .requests import Request


class QueryParam:
    """Query parameter configuration"""

    def __init__(
        self, default: Any = ..., description: str = None, example: Any = None, deprecated: bool = False, **kwargs
    ):
        self.default = default
        self.description = description
        self.example = example
        self.deprecated = deprecated
        self.kwargs = kwargs


class PathParam:
    """Path parameter configuration"""

    def __init__(self, description: str = None, example: Any = None, deprecated: bool = False, **kwargs):
        self.description = description
        self.example = example
        self.deprecated = deprecated
        self.kwargs = kwargs


class Body:
    """Request body configuration"""

    def __init__(self, description: str = None, example: Any = None, **kwargs):
        self.description = description
        self.example = example
        self.kwargs = kwargs


def Query(default: Any = ..., **kwargs) -> Any:
    """Create query parameter annotation.

    Typed as Any so mypy accepts its use as a default value for parameters with
    concrete annotations (e.g., str, int, UUID, Optional[bool]).
    """
    return QueryParam(default=default, **kwargs)


def Path(**kwargs) -> Any:
    """Create path parameter annotation.

    Typed as Any so mypy accepts its use as a default value for parameters with
    concrete annotations (e.g., UUID).
    """
    return PathParam(**kwargs)


class TypeExtractor:
    """Extract and validate types from function signatures"""

    @staticmethod
    def get_type_info(annotation: Any) -> Dict[str, Any]:
        """Extract type information from annotation"""
        if annotation == inspect.Parameter.empty:
            return {"type": "any", "required": True}

        origin = get_origin(annotation)
        args = get_args(annotation)

        # Handle Optional types
        if origin is Union and len(args) == 2 and type(None) in args:
            # Optional type
            inner_type = args[0] if args[1] is type(None) else args[1]
            return {"type": TypeExtractor._get_python_type_name(inner_type), "required": False, "nullable": True}

        # Handle List types
        if origin is list or origin is List:
            item_type = args[0] if args else Any
            return {"type": "array", "items": TypeExtractor._get_python_type_name(item_type), "required": True}

        # Handle Dict types
        if origin is dict or origin is Dict:
            return {"type": "object", "required": True}

        return {"type": TypeExtractor._get_python_type_name(annotation), "required": True}

    @staticmethod
    def _get_python_type_name(python_type: Type) -> str:
        """Convert Python type to string representation"""
        if python_type == str:
            return "string"
        elif python_type == int:
            return "integer"
        elif python_type == float:
            return "number"
        elif python_type == bool:
            return "boolean"
        elif python_type == datetime:
            return "datetime"
        elif python_type == UUID:
            return "uuid"
        elif issubclass(python_type, Enum):
            return "enum"
        elif issubclass(python_type, BaseModel):
            return "model"
        else:
            return "any"

    @staticmethod
    def validate_and_convert(value: Any, target_type: Type) -> Any:
        """Validate and convert value to target type"""
        if target_type == inspect.Parameter.empty:
            return value

        origin = get_origin(target_type)
        args = get_args(target_type)

        # Handle None values
        if value is None:
            if origin is Union and type(None) in args:
                return None
            raise ValidationError(f"Value cannot be None for type {target_type}")

        # Handle Optional types
        if origin is Union and len(args) == 2 and type(None) in args:
            inner_type = args[0] if args[1] is type(None) else args[1]
            return TypeExtractor.validate_and_convert(value, inner_type)

        # Handle List types
        if origin is list or origin is List:
            if not isinstance(value, list):
                raise ValidationError(f"Expected list, got {type(value)}")
            item_type = args[0] if args else Any
            if item_type != Any:
                return [TypeExtractor.validate_and_convert(item, item_type) for item in value]
            return value

        # Handle basic types
        if target_type == str:
            return str(value)
        elif target_type == int:
            try:
                return int(value)
            except (ValueError, TypeError):
                raise ValidationError(f"Could not convert '{value}' to integer")
        elif target_type == float:
            try:
                return float(value)
            except (ValueError, TypeError):
                raise ValidationError(f"Could not convert '{value}' to float")
        elif target_type == bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                if value.lower() in ("true", "1", "yes", "on"):
                    return True
                elif value.lower() in ("false", "0", "no", "off"):
                    return False
            raise ValidationError(f"Could not convert '{value}' to boolean")
        elif target_type == datetime:
            if isinstance(value, datetime):
                return value
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    raise ValidationError(f"Could not parse datetime: {value}")
        elif target_type == UUID:
            if isinstance(value, UUID):
                return value
            try:
                return UUID(str(value))
            except ValueError:
                raise ValidationError(f"Invalid UUID: {value}")
        elif issubclass(target_type, BaseModel):
            if isinstance(value, target_type):
                return value
            if isinstance(value, dict):
                try:
                    return target_type(**value)
                except PydanticValidationError as e:
                    raise ValidationError(f"Pydantic validation error: {e}")
            raise ValidationError(f"Could not convert to {target_type}")

        return value


class RequestProcessor:
    """Process requests with type validation"""

    @staticmethod
    async def process_parameters(
        func: Callable, request: Union[Request, StarletteRequest], path_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process and validate function parameters from request"""

        # Get function signature
        signature = inspect.signature(func)
        type_hints = get_type_hints(func)

        processed_params = {}

        for param_name, param in signature.parameters.items():
            # Skip self, request parameters
            if param_name in ("self", "request"):
                continue

            annotation = type_hints.get(param_name, param.annotation)

            # Check if it's a path parameter
            if param_name in path_params:
                try:
                    processed_params[param_name] = TypeExtractor.validate_and_convert(
                        path_params[param_name], annotation
                    )
                except ValidationError as e:
                    raise ValidationError(f"Path parameter '{param_name}': {str(e)}")
                continue

            # Check if it's a query parameter with Query annotation
            if param.default and isinstance(param.default, QueryParam):
                query_config = param.default

                # Get value from query params
                if isinstance(request, Request):
                    query_params = dict(request.query_params)
                else:
                    query_params = dict(request.query_params)

                value = query_params.get(param_name)

                if value is None:
                    if query_config.default is not ...:
                        processed_params[param_name] = query_config.default
                    elif TypeExtractor.get_type_info(annotation).get("required", True):
                        raise ValidationError(f"Query parameter '{param_name}' is required")
                else:
                    try:
                        processed_params[param_name] = TypeExtractor.validate_and_convert(value, annotation)
                    except ValidationError as e:
                        raise ValidationError(f"Query parameter '{param_name}': {str(e)}")
                continue

            # Handle request body
            if annotation != inspect.Parameter.empty and hasattr(annotation, "__annotations__"):
                # This is likely a Pydantic model for request body
                if isinstance(request, Request):
                    body = await request.json()
                else:
                    body_bytes = await request.body()
                    if body_bytes:
                        body = json.loads(body_bytes)
                    else:
                        body = {}

                try:
                    processed_params[param_name] = TypeExtractor.validate_and_convert(body, annotation)
                except ValidationError as e:
                    raise ValidationError(f"Request body validation failed: {str(e)}")
                continue

            # Default parameter handling
            if param.default != inspect.Parameter.empty:
                processed_params[param_name] = param.default
            elif TypeExtractor.get_type_info(annotation).get("required", True):
                raise ValidationError(f"Parameter '{param_name}' is required")

        return processed_params


def typed_route(func: Callable) -> Callable:
    """Decorator to enable automatic type validation for route handlers"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract request and other arguments
        request = None
        for arg in args:
            if isinstance(arg, (Request, StarletteRequest)):
                request = arg
                break

        if not request:
            # Try to find request in kwargs
            request = kwargs.get("request")

        if not request:
            raise RuntimeError("No request object found in route handler")

        # Process and validate parameters
        try:
            # Extract path parameters
            path_params = getattr(request, "path_params", {})

            # Process all parameters
            processed_params = await RequestProcessor.process_parameters(func, request, path_params)

            # Call original function with processed parameters
            if inspect.iscoroutinefunction(func):
                return await func(request, **processed_params)
            else:
                return func(request, **processed_params)

        except ValidationError as e:
            from .responses import ErrorResponse

            return ErrorResponse(message="Validation error", status_code=422, details={"validation_errors": str(e)})

    # Preserve reference to original function for schema generation
    setattr(wrapper, "_original_func", func)

    return wrapper


class TypedResponse(BaseModel):
    """Base class for typed responses"""

    pass


def response_model(model_class: Type[BaseModel]):
    """Decorator to specify response model for a route"""

    def decorator(func: Callable) -> Callable:
        setattr(func, "_response_model", model_class)
        return func

    return decorator
