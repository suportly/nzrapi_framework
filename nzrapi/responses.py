"""
Response classes for NzrApi framework

This module provides abstractions over Starlette responses,
so users don't need to import from Starlette directly.
"""

import json
from typing import Any, Dict, Optional, Union

from starlette.responses import FileResponse as StarletteFileResponse
from starlette.responses import HTMLResponse as StarletteHTMLResponse
from starlette.responses import JSONResponse as StarletteJSONResponse
from starlette.responses import PlainTextResponse as StarlettePlainTextResponse
from starlette.responses import RedirectResponse as StarletteRedirectResponse
from starlette.responses import StreamingResponse as StarletteStreamingResponse


# Re-export Starlette responses with nzrapi abstractions
class JSONResponse(StarletteJSONResponse):
    """JSON response class - abstraction over Starlette JSONResponse"""

    pass


class HTMLResponse(StarletteHTMLResponse):
    """HTML response class - abstraction over Starlette HTMLResponse"""

    pass


class PlainTextResponse(StarlettePlainTextResponse):
    """Plain text response class - abstraction over Starlette PlainTextResponse"""

    pass


class RedirectResponse(StarletteRedirectResponse):
    """Redirect response class - abstraction over Starlette RedirectResponse"""

    pass


class FileResponse(StarletteFileResponse):
    """File response class - abstraction over Starlette FileResponse"""

    pass


class StreamingResponse(StarletteStreamingResponse):
    """Streaming response class - abstraction over Starlette StreamingResponse"""

    pass


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
