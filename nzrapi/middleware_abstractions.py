"""
Middleware abstractions for NzrApi framework

This module provides abstractions over Starlette middleware,
so users don't need to import from Starlette directly.
"""

from typing import Any, Dict, List, Type

from starlette.middleware import Middleware as StarletteMiddleware
from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware


class Middleware(StarletteMiddleware):
    """Middleware class - abstraction over Starlette Middleware"""

    pass


class CORSMiddleware(StarletteCORSMiddleware):
    """CORS Middleware class - abstraction over Starlette CORSMiddleware"""

    pass


def create_cors_middleware(
    allow_origins: List[str] = None,
    allow_methods: List[str] = None,
    allow_headers: List[str] = None,
    allow_credentials: bool = False,
    allow_origin_regex: str = None,
    expose_headers: List[str] = None,
    max_age: int = 600,
) -> Middleware:
    """
    Create a CORS middleware with the specified configuration.

    Args:
        allow_origins: List of allowed origins
        allow_methods: List of allowed HTTP methods
        allow_headers: List of allowed headers
        allow_credentials: Whether to allow credentials
        allow_origin_regex: Regex pattern for allowed origins
        expose_headers: List of headers to expose to the client
        max_age: Maximum age for preflight requests

    Returns:
        Configured CORS middleware
    """
    return Middleware(
        CORSMiddleware,
        allow_origins=allow_origins or ["*"],
        allow_methods=allow_methods or ["*"],
        allow_headers=allow_headers or ["*"],
        allow_credentials=allow_credentials,
        allow_origin_regex=allow_origin_regex,
        expose_headers=expose_headers,
        max_age=max_age,
    )
