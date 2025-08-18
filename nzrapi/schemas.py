from typing import Any, Dict, Sequence

from starlette.routing import BaseRoute, Route
from starlette.schemas import SchemaGenerator

from .filters import OrderingFilter, QueryParameterFilterBackend, SearchFilter


class NzrApiSchemaGenerator(SchemaGenerator):
    """Custom schema generator to read additional OpenAPI info from endpoints."""

    def get_schema(self, routes: Sequence[BaseRoute]) -> Dict[str, Any]:
        """Generate the OpenAPI schema."""
        schema = super().get_schema(routes=list(routes))
        schema["openapi"] = "3.0.2"
        return schema

    def get_operation_for_route(self, route: Route, method: str) -> Dict[str, Any]:  # type: ignore
        operation = super().get_operation(route, method)  # type: ignore

        # Check for custom docs provided by the @docs decorator
        if hasattr(route.endpoint, "_openapi_docs"):
            custom_docs = route.endpoint._openapi_docs
            for key, value in custom_docs.items():
                if value is not None:
                    # OpenAPI uses 'requestBody', not 'request_body'
                    if key == "request_body":
                        operation["requestBody"] = value
                    else:
                        operation[key] = value

        # Use endpoint's docstring as a fallback for description
        if not operation.get("description") and route.endpoint.__doc__:
            operation["description"] = route.endpoint.__doc__.strip()

        # Use endpoint's name as a fallback for summary
        if not operation.get("summary"):
            operation["summary"] = route.name.replace("_", " ").title()

        # Auto-generate parameters for pagination and filtering
        if hasattr(route.endpoint, "view_class") and method.lower() == "get":
            view_class = route.endpoint.view_class
            self._add_pagination_params(operation, view_class)
            self._add_filter_params(operation, view_class)
            self._add_ordering_params(operation, view_class)
            self._add_search_params(operation, view_class)

        return operation

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
