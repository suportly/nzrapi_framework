"""
NzrApi Framework - Modern async framework for AI APIs with MCP support
"""

from .app import NzrApiApp
from .exceptions import (
    AuthenticationError,
    ModelNotFoundError,
    NzrApiException,
    ValidationError,
)
from .requests import Request
from .responses import JSONResponse
from .routing import Router
from .serializers import BaseSerializer, ModelSerializer

__version__ = "1.0.0"
__author__ = "NzrApi Team"

__all__ = [
    "NzrApiApp",
    "Router",
    "Request",
    "Response",
    "JSONResponse",
    "BaseSerializer",
    "ModelSerializer",
    "NzrApiException",
    "ValidationError",
    "ModelNotFoundError",
    "AuthenticationError",
]
