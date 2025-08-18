"""
Advanced routing system for NzrApi framework
"""

import asyncio
import inspect
from typing import Any, Callable, Dict, List, Optional, Union

from starlette.responses import Response as StarletteResponse
from starlette.routing import Route
from starlette.routing import Router as StarletteRouter

from .exceptions import NzrApiException
from .requests import Request
from .responses import ErrorResponse, JSONResponse


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

    def add_api_view(self, path: str, view_class: Callable, **kwargs):
        """Register a class-based view"""
        view_methods = [m.upper() for m in dir(view_class) if m in ["get", "post", "put", "patch", "delete"]]

        async def view_wrapper(request):
            # The handler from as_view() expects keyword arguments for path parameters
            handler = view_class.as_view()
            return await handler(request, **request.path_params)

        full_path = self.prefix + path
        route = Route(full_path, endpoint=view_wrapper, methods=view_methods, **kwargs)
        self.routes.append(route)

    def _route(self, method: str, path: str, **kwargs):
        """Register a route with the given method"""

        def decorator(handler: Callable):
            full_path = self.prefix + path
            route = Route(full_path, handler, methods=[method], **kwargs)
            self.routes.append(route)
            return handler

        return decorator

    def add_route(self, path: str, endpoint: Callable, **kwargs):
        """Add a route directly."""
        full_path = self.prefix + path
        route = Route(full_path, endpoint, **kwargs)
        self.routes.append(route)

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
