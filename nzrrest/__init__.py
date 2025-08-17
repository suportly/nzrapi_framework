"""
nzrRest Framework - Modern async framework for AI APIs with MCP support
"""

from .app import NzrRestApp
from .exceptions import (
    AuthenticationError,
    ModelNotFoundError,
    NzrRestException,
    ValidationError,
)
from .requests import Request
from .responses import JSONResponse, Response
from .routing import Router
from .serializers import BaseSerializer, ModelSerializer

__version__ = "1.0.0"
__author__ = "nzrRest Team"

__all__ = [
    "NzrRestApp",
    "Router",
    "Request",
    "Response",
    "JSONResponse",
    "BaseSerializer",
    "ModelSerializer",
    "NzrRestException",
    "ValidationError",
    "ModelNotFoundError",
    "AuthenticationError",
]
