"""
Tests for nzrRest application core functionality
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from nzrrest import JSONResponse, NzrRestApp, Router


@pytest.fixture
def app():
    """Create test application"""
    return NzrRestApp(debug=True)


@pytest.fixture
async def async_app():
    """Create async test application"""
    app = NzrRestApp(debug=True)
    await app.startup()
    yield app
    await app.shutdown()


class TestNzrRestApp:
    """Test NzrRestApp functionality"""

    def test_app_creation(self):
        """Test basic app creation"""
        app = NzrRestApp(title="Test API", version="1.0.0", debug=True)

        assert app.title == "Test API"
        assert app.version == "1.0.0"
        assert app.debug is True
        assert app.ai_registry is not None
        assert app.router is not None

    def test_app_with_database(self):
        """Test app creation with database"""
        database_url = "sqlite+aiosqlite:///:memory:"
        app = NzrRestApp(database_url=database_url, debug=True)

        assert app.database_url == database_url
        assert app.db_manager is not None

    def test_middleware_addition(self, app):
        """Test adding middleware to app"""
        from starlette.middleware.cors import CORSMiddleware

        initial_count = len(app.middleware_stack)
        app.add_middleware(CORSMiddleware, allow_origins=["*"])

        assert len(app.middleware_stack) == initial_count + 1

    def test_router_inclusion(self, app):
        """Test including routers"""
        router = Router()

        @router.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        initial_routes = len(app.router.routes)
        app.include_router(router, prefix="/api")

        # Routes should be added
        assert len(app.router.routes) > initial_routes

    @pytest.mark.asyncio
    async def test_startup_shutdown(self):
        """Test app startup and shutdown"""
        app = NzrRestApp(debug=True)

        # Test startup
        await app.startup()
        assert app.ai_registry is not None

        # Test shutdown
        await app.shutdown()
        # Ensure cleanup completed without errors

    def test_route_decorators(self, app):
        """Test route decorator methods"""

        @app.get("/get-test")
        async def get_test():
            return {"method": "GET"}

        @app.post("/post-test")
        async def post_test():
            return {"method": "POST"}

        @app.put("/put-test")
        async def put_test():
            return {"method": "PUT"}

        @app.delete("/delete-test")
        async def delete_test():
            return {"method": "DELETE"}

        # Check that routes were added
        routes = app.router.routes
        route_paths = [route.path for route in routes]

        assert "/get-test" in route_paths
        assert "/post-test" in route_paths
        assert "/put-test" in route_paths
        assert "/delete-test" in route_paths

    def test_exception_handlers(self, app):
        """Test exception handler registration"""

        @app.exception_handler(ValueError)
        async def value_error_handler(request, exc):
            return JSONResponse({"error": "Value error occurred"}, status_code=400)

        assert ValueError in app.exception_handlers
        assert app.exception_handlers[ValueError] == value_error_handler

    def test_startup_shutdown_handlers(self, app):
        """Test startup and shutdown handler registration"""

        startup_called = False
        shutdown_called = False

        @app.on_startup
        async def startup_handler():
            nonlocal startup_called
            startup_called = True

        @app.on_shutdown
        async def shutdown_handler():
            nonlocal shutdown_called
            shutdown_called = True

        assert startup_handler in app.startup_handlers
        assert shutdown_handler in app.shutdown_handlers


class TestRouterIntegration:
    """Test router integration with app"""

    @pytest.mark.asyncio
    async def test_nested_routers(self):
        """Test nested router inclusion"""
        app = NzrRestApp(debug=True)

        # Create nested routers
        api_router = Router()
        v1_router = Router()

        @v1_router.get("/users")
        async def list_users():
            return {"users": []}

        @api_router.get("/status")
        async def api_status():
            return {"status": "ok"}

        # Include nested routers
        api_router.include_router(v1_router, prefix="/v1")
        app.include_router(api_router, prefix="/api")

        # Verify routes are properly nested
        routes = app.router.routes
        route_paths = [route.path for route in routes]

        assert "/api/status" in route_paths
        assert "/api/v1/users" in route_paths


@pytest.mark.asyncio
async def test_asgi_interface():
    """Test ASGI interface compliance"""
    app = NzrRestApp(debug=True)

    # Mock ASGI scope, receive, send
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "query_string": b"",
        "headers": [],
    }

    receive = AsyncMock()
    send = AsyncMock()

    # Test that app is callable as ASGI app
    assert callable(app)

    # Note: Full ASGI testing would require more complex setup
    # This just verifies the interface exists
