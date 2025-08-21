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
