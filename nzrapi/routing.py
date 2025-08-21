"""
Advanced routing system for NzrApi framework with advanced type safety
"""

import asyncio
import inspect
from typing import Any, Callable, Dict, List, Optional, Type, Union, cast

from pydantic import BaseModel
from starlette.responses import Response as StarletteResponse
from starlette.routing import Route
from starlette.routing import Router as StarletteRouter
from starlette.routing import WebSocketRoute

from .dependencies import default_injector, inject_dependencies
from .exceptions import NzrApiException
from .requests import Request
from .responses import ErrorResponse, JSONResponse
from .typing import TypedResponse, typed_route
from .websockets import WebSocket, WebSocketEndpoint, WebSocketManager, default_manager


class Router:
    """Enhanced router with middleware and dependency injection support"""

    def __init__(self, prefix: str = "", tags: Optional[List[str]] = None):
        self.prefix = prefix
        self.tags = tags or []
        self.routes: List[Union[Route, WebSocketRoute]] = []
        self.middleware: List[Callable] = []
        self.dependencies: Dict[str, Callable] = {}
        self.websocket_manager = default_manager

    def add_middleware(self, middleware: Callable):
        """Add middleware to this router"""
        self.middleware.append(middleware)

    def add_dependency(self, name: str, dependency: Callable):
        """Add a dependency that can be injected into route handlers"""
        self.dependencies[name] = dependency

    def get(
        self,
        path: str,
        response_model: Optional[Type[BaseModel]] = None,
        auto_validate: bool = True,
        dependencies: bool = True,
        **kwargs,
    ):
        """Register GET route with optional type safety and dependency injection"""
        return self._route(
            "GET", path, response_model=response_model, auto_validate=auto_validate, dependencies=dependencies, **kwargs
        )

    def post(
        self,
        path: str,
        response_model: Optional[Type[BaseModel]] = None,
        auto_validate: bool = True,
        dependencies: bool = True,
        **kwargs,
    ):
        """Register POST route with optional type safety and dependency injection"""
        return self._route(
            "POST",
            path,
            response_model=response_model,
            auto_validate=auto_validate,
            dependencies=dependencies,
            **kwargs,
        )

    def put(
        self,
        path: str,
        response_model: Optional[Type[BaseModel]] = None,
        auto_validate: bool = True,
        dependencies: bool = True,
        **kwargs,
    ):
        """Register PUT route with optional type safety and dependency injection"""
        return self._route(
            "PUT", path, response_model=response_model, auto_validate=auto_validate, dependencies=dependencies, **kwargs
        )

    def patch(
        self,
        path: str,
        response_model: Optional[Type[BaseModel]] = None,
        auto_validate: bool = True,
        dependencies: bool = True,
        **kwargs,
    ):
        """Register PATCH route with optional type safety and dependency injection"""
        return self._route(
            "PATCH",
            path,
            response_model=response_model,
            auto_validate=auto_validate,
            dependencies=dependencies,
            **kwargs,
        )

    def delete(
        self,
        path: str,
        response_model: Optional[Type[BaseModel]] = None,
        auto_validate: bool = True,
        dependencies: bool = True,
        **kwargs,
    ):
        """Register DELETE route with optional type safety and dependency injection"""
        return self._route(
            "DELETE",
            path,
            response_model=response_model,
            auto_validate=auto_validate,
            dependencies=dependencies,
            **kwargs,
        )

    def add_api_view(self, path: str, view_class: Callable, **kwargs):
        """Register a class-based view"""
        view_methods = [m.upper() for m in dir(view_class) if m in ["get", "post", "put", "patch", "delete"]]

        async def view_wrapper(request):
            # The handler from as_view() expects keyword arguments for path parameters
            handler = view_class.as_view()
            return await handler(request, **request.path_params)

        full_path = self.prefix + path
        # Attach metadata for schema generation
        setattr(view_wrapper, "view_class", view_class)

        route = Route(full_path, endpoint=view_wrapper, methods=view_methods, **kwargs)
        self.routes.append(route)

    def _route(
        self,
        method: str,
        path: str,
        response_model: Optional[Type[BaseModel]] = None,
        auto_validate: bool = True,
        dependencies: bool = True,
        **kwargs,
    ):
        """Register a route with the given method and optional type safety"""

        def decorator(handler: Callable):
            # Apply dependency injection if enabled
            if dependencies:
                handler = inject_dependencies(handler)

            # Apply automatic type validation if enabled
            if auto_validate:
                handler = typed_route(handler)

            # Store response model information
            if response_model:
                setattr(handler, "_response_model", response_model)

            full_path = self.prefix + path
            route = Route(full_path, handler, methods=[method], **kwargs)

            # Store additional metadata for OpenAPI generation
            setattr(
                route,
                "_nzrapi_metadata",
                {
                    "response_model": response_model,
                    "auto_validate": auto_validate,
                    "dependencies": dependencies,
                    "original_handler": getattr(handler, "_original_func", handler),
                },
            )

            self.routes.append(route)
            return handler

        return decorator

    def websocket(self, path: str, **kwargs):
        """Register WebSocket route"""

        def decorator(endpoint: Union[Callable, WebSocketEndpoint]):
            full_path = self.prefix + path

            if isinstance(endpoint, WebSocketEndpoint):
                # Class-based WebSocket endpoint
                route = WebSocketRoute(full_path, endpoint, **kwargs)
            else:
                # Function-based WebSocket endpoint
                router_ref = self

                class FunctionWebSocketEndpoint(WebSocketEndpoint):
                    def __init__(self):
                        super().__init__(manager=router_ref.websocket_manager)

                    async def on_receive(self, websocket: WebSocket, connection_id: str, data: Any):
                        func = cast(Callable[[WebSocket, Any], Any], endpoint)
                        result = func(websocket, data)
                        if inspect.isawaitable(result):
                            await result

                route = WebSocketRoute(full_path, FunctionWebSocketEndpoint(), **kwargs)

            # Store additional metadata
            setattr(route, "_nzrapi_websocket", True)
            setattr(route, "_nzrapi_manager", self.websocket_manager)

            self.routes.append(route)
            return endpoint

        return decorator

    def websocket_route(self, path: str, endpoint: Union[Callable, WebSocketEndpoint], **kwargs):
        """Add WebSocket route directly"""
        full_path = self.prefix + path

        if isinstance(endpoint, WebSocketEndpoint):
            route = WebSocketRoute(full_path, endpoint, **kwargs)
        else:
            # Wrap function in WebSocket endpoint class
            router_ref = self

            class FunctionWebSocketEndpoint(WebSocketEndpoint):
                def __init__(self):
                    super().__init__(manager=router_ref.websocket_manager)

                async def on_receive(self, websocket: WebSocket, connection_id: str, data: Any):
                    func = cast(Callable[[WebSocket, Any], Any], endpoint)
                    result = func(websocket, data)
                    if inspect.isawaitable(result):
                        await result

            route = WebSocketRoute(full_path, FunctionWebSocketEndpoint(), **kwargs)

        setattr(route, "_nzrapi_websocket", True)
        setattr(route, "_nzrapi_manager", self.websocket_manager)

        self.routes.append(route)

    def add_route(self, path: str, endpoint: Callable, **kwargs):
        """Add a route directly."""
        full_path = self.prefix + path
        # If the endpoint accepts **kwargs, wrap it to forward path params
        try:
            sig = inspect.signature(endpoint)
            accepts_kwargs = any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values())
        except (TypeError, ValueError):
            accepts_kwargs = False

        if accepts_kwargs:

            async def endpoint_wrapper(request):
                return await endpoint(request, **request.path_params)

            # Propagate metadata for schema generation if present (e.g., view_class)
            for attr in ("view_class", "_response_model", "_openapi_docs"):
                if hasattr(endpoint, attr):
                    setattr(endpoint_wrapper, attr, getattr(endpoint, attr))

            route = Route(full_path, endpoint_wrapper, **kwargs)
        else:
            route = Route(full_path, endpoint, **kwargs)

        self.routes.append(route)

    def include_router(self, router: "Router", prefix: str = ""):
        """Include another router's routes"""
        for route in router.routes:
            # Adjust the path with the new prefix
            new_path = prefix + route.path
            if isinstance(route, Route):
                new_route: Union[Route, WebSocketRoute] = Route(
                    new_path, route.endpoint, methods=route.methods, name=route.name
                )
            else:
                # It's a WebSocketRoute
                new_route = WebSocketRoute(new_path, route.endpoint, name=route.name)
            self.routes.append(new_route)

    def to_starlette_router(self) -> StarletteRouter:
        """Convert to Starlette router"""
        return StarletteRouter(routes=self.routes)
