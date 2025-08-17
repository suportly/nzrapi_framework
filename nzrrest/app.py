"""
Main application class for nzrRest framework
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse as StarletteJSONResponse
from starlette.responses import Response
from starlette.websockets import WebSocket

from .ai.registry import AIRegistry
from .db import DatabaseManager
from .exceptions import NzrRestException
from .responses import ErrorResponse
from .routing import Router


class NzrRestApp:
    """Main application class with AI model management and async database support"""

    def __init__(
        self,
        database_url: Optional[str] = None,
        debug: bool = False,
        title: str = "nzrRest API",
        version: str = "1.0.0",
    ):
        self.database_url = database_url
        self.debug = debug
        self.title = title
        self.version = version

        # Core components
        self.db_manager = DatabaseManager(database_url) if database_url else None
        self.ai_registry = AIRegistry()

        # Application state
        self.middleware_stack: List[Middleware] = []
        self.startup_handlers: List[Callable] = []
        self.shutdown_handlers: List[Callable] = []
        # Starlette exception handler type
        ExceptionHandler = (
            Callable[
                [Request, Exception],
                Union[Response, Awaitable[Response]],
            ]
            | Callable[[WebSocket, Exception], Awaitable[None]]
        )

        self.exception_handlers: Dict[Any, ExceptionHandler] = {}

        # Router for the app
        self.router = Router()

        # Starlette app (created lazily)
        self._app: Optional[Starlette] = None

    def add_middleware(self, middleware_class, **options):
        """Add middleware to the application"""
        self.middleware_stack.append(Middleware(middleware_class, **options))

    def on_startup(self, func: Callable):
        """Register startup handler"""
        self.startup_handlers.append(func)
        return func

    def on_shutdown(self, func: Callable):
        """Register shutdown handler"""
        self.shutdown_handlers.append(func)
        return func

    def exception_handler(self, exc_class_or_status_code):
        """Register exception handler"""

        def decorator(func: Callable):
            self.exception_handlers[exc_class_or_status_code] = func
            return func

        return decorator

    def include_router(self, router: Router, prefix: str = "", tags: Optional[List[str]] = None):
        """Include a router in the application"""
        # Add tags
        if tags:
            router.tags.extend(tags)

        # Add router's routes to main router with the prefix
        self.router.include_router(router, prefix=prefix)

    async def startup(self):
        """Application startup logic"""
        # Initialize database
        if self.db_manager:
            await self.db_manager.connect()

        # Initialize AI registry
        await self.ai_registry.initialize()

        # Run custom startup handlers
        for handler in self.startup_handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler()
            else:
                handler()

    async def shutdown(self):
        """Application shutdown logic"""
        # Run custom shutdown handlers
        for handler in self.shutdown_handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler()
            else:
                handler()

        # Cleanup AI registry
        await self.ai_registry.cleanup()

        # Close database connections
        if self.db_manager:
            await self.db_manager.disconnect()

    @asynccontextmanager
    async def get_db_session(self):
        """Get database session context manager"""
        if not self.db_manager:
            raise RuntimeError("Database not configured")

        async with self.db_manager.get_session() as session:
            yield session

    def _create_starlette_app(self) -> Starlette:
        """Create the underlying Starlette application"""

        # Default exception handlers
        default_exception_handlers = {
            NzrRestException: self._handle_nzrrest_exception,
            Exception: self._handle_generic_exception,
        }

        # Merge with custom exception handlers
        all_exception_handlers = {
            **default_exception_handlers,
            **self.exception_handlers,
        }

        # Create Starlette app
        app = Starlette(
            debug=self.debug,
            routes=self.router.routes,
            middleware=self.middleware_stack,
            exception_handlers=all_exception_handlers,
            on_startup=[self.startup],
            on_shutdown=[self.shutdown],
        )

        return app

    async def _handle_nzrrest_exception(self, request: Request, exc: Exception) -> Response:
        assert isinstance(exc, NzrRestException)
        """Handle nzrRest framework exceptions"""
        return ErrorResponse(
            message=exc.message, status_code=exc.status_code, details=exc.details
        ).to_starlette_response()

    async def _handle_generic_exception(self, request: Request, exc: Exception):
        """Handle generic exceptions"""
        if self.debug:
            # In debug mode, show full exception details
            import traceback

            return ErrorResponse(
                message="Internal server error",
                status_code=500,
                details={
                    "error": str(exc),
                    "type": type(exc).__name__,
                    "traceback": traceback.format_exc(),
                },
            ).to_starlette_response()
        else:
            # In production, hide exception details
            return ErrorResponse(message="Internal server error", status_code=500).to_starlette_response()

    @property
    def app(self) -> Starlette:
        """Get the Starlette application instance"""
        if self._app is None:
            self._app = self._create_starlette_app()
        return self._app

    def __call__(self, scope, receive, send):
        """ASGI application interface"""
        return self.app(scope, receive, send)

    # Convenience methods for adding routes directly to the app
    def get(self, path: str, **kwargs):
        """Register GET route on main router"""
        return self.router.get(path, **kwargs)

    def post(self, path: str, **kwargs):
        """Register POST route on main router"""
        return self.router.post(path, **kwargs)

    def put(self, path: str, **kwargs):
        """Register PUT route on main router"""
        return self.router.put(path, **kwargs)

    def patch(self, path: str, **kwargs):
        """Register PATCH route on main router"""
        return self.router.patch(path, **kwargs)

    def delete(self, path: str, **kwargs):
        """Register DELETE route on main router"""
        return self.router.delete(path, **kwargs)
