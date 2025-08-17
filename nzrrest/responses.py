"""
Response classes for nzrRest framework
"""

import json
from typing import Any, Dict, Optional, Union

from starlette.responses import JSONResponse as StarletteJSONResponse
from starlette.responses import Response as StarletteResponse


class Response:
    """Base response class"""

    def __init__(
        self,
        content: Union[str, bytes] = "",
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
    ):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}
        self.media_type = media_type

    def to_starlette_response(self) -> StarletteResponse:
        """Convert to Starlette response"""
        return StarletteResponse(
            content=self.content,
            status_code=self.status_code,
            headers=self.headers,
            media_type=self.media_type,
        )


class JSONResponse(Response):
    """JSON response class with enhanced functionality"""

    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        ensure_ascii: bool = False,
        indent: Optional[int] = None,
    ):
        self.raw_content = content
        self.ensure_ascii = ensure_ascii
        self.indent = indent

        # Serialize content to JSON
        json_content = self._serialize_content(content)

        # Set default headers
        json_headers = headers or {}
        json_headers.setdefault("content-type", "application/json")

        super().__init__(
            content=json_content,
            status_code=status_code,
            headers=json_headers,
            media_type="application/json",
        )

    def _serialize_content(self, content: Any) -> str:
        """Serialize content to JSON string"""
        if content is None:
            return "{}"

        try:
            return json.dumps(
                content,
                ensure_ascii=self.ensure_ascii,
                indent=self.indent,
                default=self._json_serializer,
            )
        except (TypeError, ValueError) as e:
            raise ValueError(f"Unable to serialize content to JSON: {e}")

    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for special objects"""
        # Handle common non-serializable types
        if hasattr(obj, "isoformat"):  # datetime objects
            return obj.isoformat()
        elif hasattr(obj, "__dict__"):  # Objects with __dict__
            return obj.__dict__
        elif hasattr(obj, "_asdict"):  # Named tuples
            return obj._asdict()
        else:
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def to_starlette_response(self) -> StarletteJSONResponse:
        """Convert to Starlette JSON response"""
        return StarletteJSONResponse(content=self.raw_content, status_code=self.status_code, headers=self.headers)


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
