"""
Main application class for NzrApi framework
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.responses import JSONResponse as StarletteJSONResponse
from starlette.responses import Response
from starlette.routing import Route, WebSocketRoute
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.websockets import WebSocket

from .ai.registry import AIRegistry
from .db import DatabaseManager
from .db.manager import DatabaseMiddleware
from .exceptions import NzrApiException
from .responses import ErrorResponse
from .routing import Router
from .schemas import NzrApiSchemaGenerator


def get_swagger_ui_html(openapi_url: str, title: str) -> HTMLResponse:
    html = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>{title} - Swagger UUI</title>
            <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css" />
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js" crossorigin></script>
            <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-standalone-preset.js" crossorigin></script>
            <script>            
                window.onload = () => {{
                    window.ui = SwaggerUIBundle({{
                        url: '{openapi_url}',
                        dom_id: '#swagger-ui',
                        presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIStandalonePreset
                        ],
                        layout: 'StandaloneLayout',
                    }});
                }};
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html)


class NzrApiApp:
    """Main application class with AI model management and async database support"""

    def __init__(
        self,
        database_url: Optional[str] = None,
        debug: bool = False,
        title: str = "NzrApi API",
        version: str = "0.2.1",
        description: Optional[str] = None,
        docs_url: Optional[str] = "/docs",
        docs_openapi_url: Optional[str] = "/openapi.json",
        middleware: Optional[List[Middleware]] = None,
    ):
        """
        Initialize NzrApi application with clean middleware configuration.

        Args:
            database_url: Database connection URL for async SQLAlchemy
            debug: Enable debug mode with detailed logging
            title: API title for documentation
            version: API version
            description: API description for documentation
            docs_url: URL path for Swagger UI documentation
            docs_openapi_url: URL path for OpenAPI JSON schema
            middleware: List of Starlette Middleware instances to configure.
                       Example:
                       middleware=[
                           Middleware(RequestIDMiddleware),
                           Middleware(TimingMiddleware),
                           Middleware(CORSMiddleware, allow_origins=["*"])
                       ]

        Example:
            >>> app = NzrApiApp(
            ...     title="My API",
            ...     middleware=[
            ...         Middleware(RequestIDMiddleware),
            ...         Middleware(CORSMiddleware, allow_origins=["*"])
            ...     ]
            ... )
        """
        self.database_url = database_url
        self.debug = debug
        self.title = title
        self.version = version
        self.description = description
        self.docs_openapi_url = docs_openapi_url
        self.docs_url = docs_url
        self.openapi_schema: Optional[Dict[str, Any]] = None

        # Core components
        self.db_manager = DatabaseManager(database_url) if database_url else None
        self.ai_registry = AIRegistry()

        # Application state
        self.middleware_stack: List[Middleware] = middleware or []
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

    def openapi(self) -> Dict[str, Any]:
        if self.openapi_schema is None:
            schema_generator = NzrApiSchemaGenerator(
                {"title": self.title, "version": self.version, "description": self.description}
            )
            self.openapi_schema = schema_generator.get_schema(routes=self.router.routes)
        return self.openapi_schema

    async def swagger_ui(self, request: Request) -> HTMLResponse:
        return get_swagger_ui_html(openapi_url=self.docs_openapi_url, title=self.title)

    async def openapi_endpoint(self, request: Request) -> StarletteJSONResponse:
        return StarletteJSONResponse(self.openapi())

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

    @asynccontextmanager
    async def get_db_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide a database session for a single request."""
        if not self.db_manager:
            raise RuntimeError("Database is not configured. Please provide a `database_url` when creating NzrApiApp.")
        async with self.db_manager.get_session() as session:
            yield session

    def include_router(self, router: Router, prefix: str = "", tags: Optional[List[str]] = None):
        """Include a router in the application"""
        # Add tags
        if tags:
            router.tags.extend(tags)

        # Add router's routes to main router with the prefix
        self.router.include_router(router, prefix=prefix)

    @asynccontextmanager
    async def lifespan(self, app: Starlette) -> AsyncGenerator[None, None]:
        """Manage application startup and shutdown events."""
        # Initialize AI registry
        self.ai_registry = AIRegistry()

        # Connect to database if configured
        if self.db_manager:
            await self.db_manager.connect()

        # Run startup handlers
        for handler in self.startup_handlers:
            await handler()

        yield

        # Run shutdown handlers
        for handler in self.shutdown_handlers:
            await handler()

        # Disconnect from database if configured
        if self.db_manager:
            await self.db_manager.disconnect()

    @property
    def app(self) -> Starlette:
        """Get the Starlette application instance"""
        if self._app is None:
            # Add routes for OpenAPI and Swagger UI if enabled
            self.router.add_route("/openapi.json", self.openapi_endpoint, include_in_schema=False)
            if self.docs_url:
                self.router.add_route(self.docs_url, self.swagger_ui, include_in_schema=False)

            # Add default exception handlers
            self.exception_handlers.setdefault(NzrApiException, self._handle_nzrapi_exception)
            self.exception_handlers.setdefault(Exception, self._handle_generic_exception)

            # Ensure database middleware is present when database is configured
            if self.db_manager:
                has_db_middleware = any(middleware.cls is DatabaseMiddleware for middleware in self.middleware_stack)
                if not has_db_middleware:
                    self.middleware_stack.append(Middleware(DatabaseMiddleware, db_manager=self.db_manager))

            # Define middleware to inject NzrApiApp into WebSocket state
            class WebSocketStateMiddleware:
                def __init__(self, app: ASGIApp, nzrapi_app: "NzrApiApp") -> None:
                    self.app = app
                    self.nzrapi_app = nzrapi_app

                async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
                    if scope["type"] == "websocket":
                        if "state" not in scope or scope["state"] is None:
                            scope["state"] = {}
                        scope["state"]["nzrapi_app"] = self.nzrapi_app
                    await self.app(scope, receive, send)

            # Add the WebSocket state middleware via Starlette's configuration
            self.middleware_stack.append(Middleware(WebSocketStateMiddleware, nzrapi_app=self))

            self._app = Starlette(
                debug=self.debug,
                routes=self.router.routes,
                middleware=self.middleware_stack,
                exception_handlers=self.exception_handlers,
                lifespan=self.lifespan,
            )

            # Store a reference to the NzrApiApp instance in the app state
            self._app.state.nzrapi_app = self

        return self._app

    async def _handle_nzrapi_exception(self, request: Request, exc: Exception) -> Response:
        assert isinstance(exc, NzrApiException)
        """Handle NzrApi framework exceptions"""
        return ErrorResponse(message=exc.message, status_code=exc.status_code, details=exc.details)

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
            )
        else:
            # In production, hide exception details
            return ErrorResponse(message="Internal server error", status_code=500)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI application interface"""
        await self.app(scope, receive, send)

    # Convenience methods for adding routes directly to the app
    def get(self, path: str, **kwargs):
        """Register GET route on main router with type safety"""
        return self.router.get(path, **kwargs)

    def post(self, path: str, **kwargs):
        """Register POST route on main router with type safety"""
        return self.router.post(path, **kwargs)

    def put(self, path: str, **kwargs):
        """Register PUT route on main router with type safety"""
        return self.router.put(path, **kwargs)

    def patch(self, path: str, **kwargs):
        """Register PATCH route on main router with type safety"""
        return self.router.patch(path, **kwargs)

    def delete(self, path: str, **kwargs):
        """Register DELETE route on main router with type safety"""
        return self.router.delete(path, **kwargs)

    def websocket(self, path: str, **kwargs):
        """Register WebSocket route on main router"""
        return self.router.websocket(path, **kwargs)
