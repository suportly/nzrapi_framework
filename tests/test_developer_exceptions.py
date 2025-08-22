"""
Tests for developer-friendly exceptions
"""

import pytest

from nzrapi.exceptions import DatabaseConfigurationError, DependencyInjectionError, DeveloperFriendlyError


class TestDeveloperFriendlyExceptions:
    """Test the developer-friendly exception system"""

    def test_developer_friendly_error_basic(self):
        """Test basic DeveloperFriendlyError functionality"""
        error = DeveloperFriendlyError("Test error message")

        # Should have the basic message
        assert "Test error message" in str(error)
        assert error.debug_info == {}
        assert error.suggestions == []

    def test_developer_friendly_error_with_debug_info(self):
        """Test DeveloperFriendlyError with debug information"""
        debug_info = {"context": "test_context", "user_id": 123, "request_path": "/api/users"}

        error = DeveloperFriendlyError("Test error with debug info", debug_info=debug_info)

        error_str = str(error)
        assert "Test error with debug info" in error_str
        assert "Debug Information:" in error_str
        assert "context: test_context" in error_str
        assert "user_id: 123" in error_str
        assert "request_path: /api/users" in error_str

        # Should store debug info
        assert error.debug_info == debug_info

    def test_developer_friendly_error_with_suggestions(self):
        """Test DeveloperFriendlyError with suggestions"""
        suggestions = [
            "Check your database connection",
            "Verify middleware is properly configured",
            "Make sure NzrApiApp is initialized correctly",
        ]

        error = DeveloperFriendlyError("Test error with suggestions", suggestions=suggestions)

        error_str = str(error)
        assert "Test error with suggestions" in error_str
        assert "Suggestions:" in error_str
        assert "1. Check your database connection" in error_str
        assert "2. Verify middleware is properly configured" in error_str
        assert "3. Make sure NzrApiApp is initialized correctly" in error_str

        # Should store suggestions
        assert error.suggestions == suggestions

    def test_developer_friendly_error_complete(self):
        """Test DeveloperFriendlyError with both debug info and suggestions"""
        debug_info = {"context": "full_test"}
        suggestions = ["Try this fix", "Or try that fix"]

        error = DeveloperFriendlyError("Complete test error", debug_info=debug_info, suggestions=suggestions)

        error_str = str(error)
        assert "Complete test error" in error_str
        assert "Debug Information:" in error_str
        assert "context: full_test" in error_str
        assert "Suggestions:" in error_str
        assert "1. Try this fix" in error_str
        assert "2. Or try that fix" in error_str

    def test_database_configuration_error_default(self):
        """Test DatabaseConfigurationError with default context"""
        error = DatabaseConfigurationError()

        error_str = str(error)
        assert "Database not properly configured in context: Unknown" in error_str
        assert "Debug Information:" in error_str
        assert "context: Unknown" in error_str
        assert "Missing database_url in NzrApiApp initialization" in error_str
        assert "DatabaseMiddleware not added to middleware stack" in error_str
        assert "Suggestions:" in error_str
        assert "Ensure NzrApiApp(database_url='your-db-url') is set" in error_str
        assert "Add DatabaseMiddleware to your middleware stack" in error_str
        assert "Check database connection string format" in error_str

    def test_database_configuration_error_custom_context(self):
        """Test DatabaseConfigurationError with custom context"""
        error = DatabaseConfigurationError("user_registration")

        error_str = str(error)
        assert "Database not properly configured in context: user_registration" in error_str
        assert "context: user_registration" in error_str

    def test_dependency_injection_error_basic(self):
        """Test DependencyInjectionError with basic parameters"""
        error = DependencyInjectionError("db_session")

        error_str = str(error)
        assert "Failed to resolve dependency: db_session" in error_str
        assert "Debug Information:" in error_str
        assert "requested_dependency: db_session" in error_str
        assert "available_dependencies: []" in error_str
        assert "Suggestions:" in error_str
        assert "Use get_session_reliable(request) instead of Depends(db_session)" in error_str
        assert "Use @with_db_session decorator for simple cases" in error_str

    def test_dependency_injection_error_with_available_deps(self):
        """Test DependencyInjectionError with available dependencies list"""
        available_deps = ["request", "user", "app"]
        error = DependencyInjectionError("missing_service", available_deps)

        error_str = str(error)
        assert "Failed to resolve dependency: missing_service" in error_str
        assert "requested_dependency: missing_service" in error_str
        assert "available_dependencies: ['request', 'user', 'app']" in error_str
        assert "Use get_session_reliable(request) instead of Depends(missing_service)" in error_str

    def test_exception_inheritance(self):
        """Test that developer-friendly exceptions inherit properly"""
        from nzrapi.exceptions import NzrApiException

        # DeveloperFriendlyError should inherit from NzrApiException
        error = DeveloperFriendlyError("test")
        assert isinstance(error, NzrApiException)
        assert isinstance(error, Exception)

        # Specific errors should inherit from DeveloperFriendlyError
        db_error = DatabaseConfigurationError()
        dep_error = DependencyInjectionError("test_dep")

        assert isinstance(db_error, DeveloperFriendlyError)
        assert isinstance(db_error, NzrApiException)

        assert isinstance(dep_error, DeveloperFriendlyError)
        assert isinstance(dep_error, NzrApiException)

    def test_empty_debug_info_and_suggestions(self):
        """Test behavior with empty debug info and suggestions"""
        error = DeveloperFriendlyError("Test message", debug_info={}, suggestions=[])

        error_str = str(error)
        assert "Test message" in error_str
        # Should not include empty sections
        assert "Debug Information:" not in error_str
        assert "Suggestions:" not in error_str

    def test_none_debug_info_and_suggestions(self):
        """Test behavior with None debug info and suggestions"""
        error = DeveloperFriendlyError("Test message", debug_info=None, suggestions=None)

        error_str = str(error)
        assert "Test message" in error_str
        # Should not include empty sections
        assert "Debug Information:" not in error_str
        assert "Suggestions:" not in error_str

        # Should have empty defaults
        assert error.debug_info == {}
        assert error.suggestions == []
