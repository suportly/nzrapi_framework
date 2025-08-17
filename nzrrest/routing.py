"""
Advanced routing system for nzrRest framework
"""

import asyncio
import inspect
from typing import Any, Callable, Dict, List, Optional, Union

from starlette.responses import Response as StarletteResponse
from starlette.routing import Route
from starlette.routing import Router as StarletteRouter

from .exceptions import NzrRestException
from .requests import Request
from .responses import ErrorResponse, JSONResponse, Response


class Router:
    """Enhanced router with middleware and dependency injection support"""

    def __init__(self, prefix: str = "", tags: Optional[List[str]] = None):
        self.prefix = prefix
        self.tags = tags or []
        self.routes: List[Route] = []
        self.middleware: List[Callable] = []
        self.dependencies: Dict[str, Callable] = {}

    def add_middleware(self, middleware: Callable):
        """Add middleware to this router"""
        self.middleware.append(middleware)

    def add_dependency(self, name: str, dependency: Callable):
        """Add a dependency that can be injected into route handlers"""
        self.dependencies[name] = dependency

    def _create_route_handler(self, handler: Callable, method: str):
        """Create a route handler with middleware and dependency injection"""

        async def route_wrapper(request):
            try:
                # Create enhanced request object
                nzr_request = Request(request)

                # Apply middleware
                for middleware in self.middleware:
                    result = await middleware(nzr_request)
                    if result is not None:
                        return self._convert_response(result)

                # Inject dependencies
                handler_kwargs = {}
                sig = inspect.signature(handler)

                for param_name, param in sig.parameters.items():
                    if param_name == "request":
                        handler_kwargs["request"] = nzr_request
                    elif param_name in self.dependencies:
                        dep_result = await self.dependencies[param_name](nzr_request)
                        handler_kwargs[param_name] = dep_result
                    elif param_name in nzr_request.path_params:
                        handler_kwargs[param_name] = nzr_request.path_params[param_name]

                # Call the handler
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(**handler_kwargs)
                else:
                    result = handler(**handler_kwargs)

                return self._convert_response(result)

            except NzrRestException as e:
                return ErrorResponse(
                    message=e.message, status_code=e.status_code, details=e.details
                ).to_starlette_response()
            except Exception as e:
                return ErrorResponse(
                    message="Internal server error",
                    status_code=500,
                    details={"error": str(e)},
                ).to_starlette_response()

        return route_wrapper

    def _convert_response(self, result: Any) -> StarletteResponse:
        """Convert handler result to Starlette response"""
        if isinstance(result, (Response, JSONResponse, ErrorResponse)):
            return result.to_starlette_response()
        elif isinstance(result, StarletteResponse):
            return result
        elif isinstance(result, dict):
            return JSONResponse(result).to_starlette_response()
        elif isinstance(result, (list, tuple)):
            return JSONResponse(list(result)).to_starlette_response()
        elif isinstance(result, str):
            return StarletteResponse(result, media_type="text/plain")
        else:
            return JSONResponse(result).to_starlette_response()

    def get(self, path: str, **kwargs):
        """Register GET route"""
        return self._route("GET", path, **kwargs)

    def post(self, path: str, **kwargs):
        """Register POST route"""
        return self._route("POST", path, **kwargs)

    def put(self, path: str, **kwargs):
        """Register PUT route"""
        return self._route("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs):
        """Register PATCH route"""
        return self._route("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs):
        """Register DELETE route"""
        return self._route("DELETE", path, **kwargs)

    def _route(self, method: str, path: str, **kwargs):
        """Register a route with the given method"""

        def decorator(handler: Callable):
            full_path = self.prefix + path
            route_handler = self._create_route_handler(handler, method)

            route = Route(full_path, route_handler, methods=[method], **kwargs)
            self.routes.append(route)
            return handler

        return decorator

    def include_router(self, router: "Router", prefix: str = ""):
        """Include another router's routes"""
        for route in router.routes:
            # Adjust the path with the new prefix
            new_path = prefix + route.path
            new_route = Route(new_path, route.endpoint, methods=route.methods, name=route.name)
            self.routes.append(new_route)

    def to_starlette_router(self) -> StarletteRouter:
        """Convert to Starlette router"""
        return StarletteRouter(routes=self.routes)
