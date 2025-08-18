"""
Response classes for NzrApi framework
"""

import json
from typing import Any, Dict, Optional, Union

from starlette.responses import JSONResponse


class ErrorResponse(JSONResponse):
    """Error response class"""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        content = {"error": {"message": message, "code": error_code, "details": details or {}}}

        super().__init__(content=content, status_code=status_code, headers=headers)


class ValidationErrorResponse(ErrorResponse):
    """Validation error response"""

    def __init__(
        self,
        errors: Dict[str, Any],
        message: str = "Validation failed",
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details={"validation_errors": errors},
            headers=headers,
        )
