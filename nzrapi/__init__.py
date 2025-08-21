"""
NzrApi Framework - Modern async framework for AI APIs with MCP support and advanced type safety
"""

from .app import NzrApiApp
from .dependencies import (
    Depends,
    authenticated_user,
    create_dependency_provider,
    get_current_user,
    get_db,
    get_db_session,
    get_db_with_commit,
    get_request,
    inject_dependencies,
    pagination,
    register_dependency,
    require_auth,
)
from .exceptions import (
    AuthenticationError,
    ModelNotFoundError,
    NzrApiException,
    ValidationError,
)
from .middleware import (
    AuthenticationMiddleware,
    CompressionMiddleware,
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    MetricsMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    TimingMiddleware,
    create_auth_middleware,
    create_cors_middleware,
    create_rate_limit_middleware,
    parse_rate_limit,
)
from .middleware_abstractions import CORSMiddleware, Middleware
from .requests import Request
from .responses import (
    ErrorResponse,
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    StreamingResponse,
    ValidationErrorResponse,
)
from .routing import Router
from .security import (
    APIKeyCookie,
    APIKeyHeader,
    APIKeyQuery,
    HTTPBasic,
    HTTPBearer,
    HTTPDigest,
    JWTBearer,
    OAuth2AuthorizationCodeBearer,
    OAuth2PasswordBearer,
    api_key_cookie,
    api_key_header,
    api_key_query,
    basic_auth,
    bearer_token,
    create_access_token,
    create_api_key_dependency,
    create_basic_auth_dependency,
    create_jwt_bearer,
    create_oauth2_password_bearer,
    generate_secret_key,
    hash_password,
    verify_password,
    verify_token,
)
from .serializers import BaseSerializer, ModelSerializer
from .typing import Body, Path, Query, TypedResponse, response_model, typed_route
from .websockets import (
    AIStreamingEndpoint,
    WebSocket,
    WebSocketDisconnect,
    WebSocketEndpoint,
    WebSocketManager,
    default_manager,
    websocket_endpoint,
)

__version__ = "1.0.0"
__author__ = "NzrApi Team"

__all__ = [
    # Core
    "NzrApiApp",
    "Router",
    "Request",
    # Response classes
    "JSONResponse",
    "HTMLResponse",
    "PlainTextResponse",
    "RedirectResponse",
    "FileResponse",
    "StreamingResponse",
    "ErrorResponse",
    "ValidationErrorResponse",
    "TypedResponse",
    # Middleware abstractions
    "Middleware",
    "CORSMiddleware",
    # Serializers
    "BaseSerializer",
    "ModelSerializer",
    # Middleware
    "RequestIDMiddleware",
    "TimingMiddleware",
    "LoggingMiddleware",
    "RateLimitMiddleware",
    "AuthenticationMiddleware",
    "ErrorHandlingMiddleware",
    "CompressionMiddleware",
    "MetricsMiddleware",
    "create_cors_middleware",
    "create_rate_limit_middleware",
    "create_auth_middleware",
    "parse_rate_limit",
    "NzrApiException",
    "ValidationError",
    "ModelNotFoundError",
    "AuthenticationError",
    # Type safety features
    "Query",
    "Path",
    "Body",
    "typed_route",
    "response_model",
    "TypedResponse",
    # WebSocket features
    "WebSocket",
    "WebSocketDisconnect",
    "WebSocketManager",
    "WebSocketEndpoint",
    "AIStreamingEndpoint",
    "default_manager",
    "websocket_endpoint",
    # Dependency injection
    "Depends",
    "inject_dependencies",
    "get_request",
    "get_db_session",
    "get_current_user",
    "pagination",
    "authenticated_user",
    "require_auth",
    "get_db",
    "get_db_with_commit",
    "register_dependency",
    "create_dependency_provider",
    # Security features
    "HTTPBasic",
    "HTTPBearer",
    "HTTPDigest",
    "JWTBearer",
    "OAuth2PasswordBearer",
    "OAuth2AuthorizationCodeBearer",
    "APIKeyQuery",
    "APIKeyHeader",
    "APIKeyCookie",
    "basic_auth",
    "bearer_token",
    "api_key_query",
    "api_key_header",
    "api_key_cookie",
    "generate_secret_key",
    "hash_password",
    "verify_password",
    "create_access_token",
    "verify_token",
    "create_jwt_bearer",
    "create_oauth2_password_bearer",
    "create_basic_auth_dependency",
    "create_api_key_dependency",
]
