"""
Tests for database session helpers
"""

from unittest.mock import AsyncMock, Mock

import pytest

from nzrapi.dependencies import db_session_dependency, get_session_reliable, quick_db_query, with_db_session
from nzrapi.requests import Request


class TestDatabaseHelpers:
    """Test the database session helper utilities"""

    def test_get_session_reliable_from_state(self):
        """Test getting session from request.state.db_session"""
        # Mock request with db_session in state
        request = Mock()
        mock_session = Mock()
        request.state.db_session = mock_session

        # Should return the session from state
        result = get_session_reliable(request)
        assert result is mock_session

    def test_get_session_reliable_from_app(self):
        """Test getting session from request.app.get_db_session"""
        # Mock request without db_session in state but with app
        request = Mock()
        request.state.db_session = None

        mock_session = Mock()
        mock_app = Mock()
        mock_app.get_db_session.return_value = mock_session
        request.app = mock_app

        # Should return the session from app
        result = get_session_reliable(request)
        assert result is mock_session
        mock_app.get_db_session.assert_called_once()

    def test_get_session_reliable_from_nzrapi_app(self):
        """Test getting session from request.state.nzrapi_app"""
        # Mock request without db_session in state, no app, but nzrapi_app in state
        request = Mock()
        request.state.db_session = None
        request.app = None  # No app attribute

        mock_session = Mock()
        mock_nzrapi_app = Mock()
        mock_nzrapi_app.get_db_session.return_value = mock_session
        request.state.nzrapi_app = mock_nzrapi_app

        # Should return the session from nzrapi_app
        result = get_session_reliable(request)
        assert result is mock_session
        mock_nzrapi_app.get_db_session.assert_called_once()

    def test_get_session_reliable_no_session_available(self):
        """Test error when no session is available"""

        # Create a simple object that has no session sources
        class MockRequest:
            def __init__(self):
                self.state = MockState()

        class MockState:
            def __init__(self):
                self.db_session = None
                self.nzrapi_app = None

        request = MockRequest()

        # Should raise RuntimeError with helpful message
        with pytest.raises(RuntimeError) as exc_info:
            get_session_reliable(request)

        error_message = str(exc_info.value)
        assert "Database session not available" in error_message

    @pytest.mark.asyncio
    async def test_with_db_session_decorator(self):
        """Test the with_db_session decorator"""
        # Mock session and request
        mock_session = Mock()
        mock_request = Mock()
        mock_request.state = Mock()
        mock_request.state.db_session = mock_session

        # Create a test function with decorator
        @with_db_session
        async def test_endpoint(request, session):
            return {"session": session, "request": request}

        # Call the decorated function
        result = await test_endpoint(mock_request)

        # Should inject session as second parameter
        assert result["session"] is mock_session
        assert result["request"] is mock_request

    @pytest.mark.asyncio
    async def test_with_db_session_decorator_kwargs(self):
        """Test the with_db_session decorator with kwargs"""
        # Mock session and request
        mock_session = Mock()
        mock_request = Mock()
        mock_request.state = Mock()
        mock_request.state.db_session = mock_session

        # Create a test function that uses session from kwargs
        @with_db_session
        async def test_endpoint(request, other_param=None, session=None):
            return {"session": session, "request": request, "other": other_param}

        # Call the decorated function
        result = await test_endpoint(mock_request, other_param="test")

        # Should inject session as kwargs
        assert result["session"] is mock_session
        assert result["request"] is mock_request
        assert result["other"] == "test"

    @pytest.mark.asyncio
    async def test_quick_db_query_function_exists(self):
        """Test that quick_db_query function exists and is callable"""
        # Test that the function is importable and callable
        assert callable(quick_db_query)

        # Test that it has the expected signature
        import inspect

        sig = inspect.signature(quick_db_query)
        params = list(sig.parameters.keys())
        assert "request" in params
        assert "model_class" in params

    def test_db_session_dependency(self):
        """Test db_session_dependency factory"""
        dependency = db_session_dependency()

        # Should return a Depends object
        from nzrapi.dependencies import Depends

        assert isinstance(dependency, Depends)
        assert dependency.dependency is not None
        assert dependency.use_cache is True

    def test_quick_db_query_imports_sqlalchemy(self):
        """Test that quick_db_query tries to import SQLAlchemy"""
        # Test that the function mentions SQLAlchemy in its implementation
        import inspect

        source = inspect.getsource(quick_db_query)
        assert "sqlalchemy" in source.lower() or "select" in source
