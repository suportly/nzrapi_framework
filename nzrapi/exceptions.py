"""
Custom exceptions for NzrApi framework
"""

from typing import Any, Dict, Optional


class NzrApiException(Exception):
    """Base exception for NzrApi framework"""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationError(NzrApiException):
    """Raised when data validation fails"""

    def __init__(
        self,
        message: str = "Validation failed",
        errors: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, status_code=400, details={"errors": errors or {}})


class NotFound(NzrApiException):
    """Raised when a resource is not found"""

    def __init__(self, message: str = "Not found"):
        super().__init__(message, status_code=404)


class ModelNotFoundError(NotFound):
    """Raised when an AI model is not found"""

    def __init__(self, message: str = "Model not found"):
        super().__init__(message)


class AuthenticationError(NzrApiException):
    """Raised when authentication fails"""

    def __init__(self, message: str = "Authentication failed", headers: Optional[Dict[str, str]] = None):
        super().__init__(message, status_code=401)
        # Optional headers such as WWW-Authenticate for auth challenges
        self.headers: Dict[str, str] = headers or {}


class PermissionDenied(NzrApiException):
    """Raised when user lacks required permissions"""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, status_code=403)


class RateLimitError(NzrApiException):
    """Raised when rate limit is exceeded"""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)


class DeveloperFriendlyError(NzrApiException):
    """Base class for errors with helpful debugging information."""

    def __init__(self, message: str, debug_info: dict = None, suggestions: list = None):
        self.debug_info = debug_info or {}
        self.suggestions = suggestions or []

        full_message = f"{message}\n"

        if self.debug_info:
            full_message += "\nDebug Information:\n"
            for key, value in self.debug_info.items():
                full_message += f"  {key}: {value}\n"

        if self.suggestions:
            full_message += "\nSuggestions:\n"
            for i, suggestion in enumerate(self.suggestions, 1):
                full_message += f"  {i}. {suggestion}\n"

        super().__init__(full_message)


class DatabaseConfigurationError(DeveloperFriendlyError):
    """Raised when database is not properly configured."""

    def __init__(self, context: str = "Unknown"):
        super().__init__(
            message=f"Database not properly configured in context: {context}",
            debug_info={
                "context": context,
                "common_causes": [
                    "Missing database_url in NzrApiApp initialization",
                    "DatabaseMiddleware not added to middleware stack",
                    "Database connection failed during startup",
                ],
            },
            suggestions=[
                "Ensure NzrApiApp(database_url='your-db-url') is set",
                "Add DatabaseMiddleware to your middleware stack",
                "Check database connection string format",
                "Verify database server is running and accessible",
            ],
        )


class DependencyInjectionError(DeveloperFriendlyError):
    """Raised when dependency injection fails with helpful context."""

    def __init__(self, dependency_name: str, available_deps: list = None):
        super().__init__(
            message=f"Failed to resolve dependency: {dependency_name}",
            debug_info={
                "requested_dependency": dependency_name,
                "available_dependencies": available_deps or [],
                "request_state_attributes": "Check request.state for available attributes",
            },
            suggestions=[
                f"Use get_session_reliable(request) instead of Depends({dependency_name})",
                "Ensure proper middleware configuration",
                "Check if dependency is registered in app",
                "Use @with_db_session decorator for simple cases",
            ],
        )
