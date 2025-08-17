"""
Custom exceptions for nzrRest framework
"""

from typing import Any, Dict, Optional


class NzrRestException(Exception):
    """Base exception for nzrRest framework"""

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


class ValidationError(NzrRestException):
    """Raised when data validation fails"""

    def __init__(
        self,
        message: str = "Validation failed",
        errors: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, status_code=400, details={"errors": errors or {}})


class ModelNotFoundError(NzrRestException):
    """Raised when an AI model is not found"""

    def __init__(self, message: str = "Model not found"):
        super().__init__(message, status_code=404)


class AuthenticationError(NzrRestException):
    """Raised when authentication fails"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class PermissionError(NzrRestException):
    """Raised when user lacks required permissions"""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, status_code=403)


class RateLimitError(NzrRestException):
    """Raised when rate limit is exceeded"""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)
