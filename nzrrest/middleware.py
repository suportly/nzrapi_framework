"""
Middleware system for nzrRest framework
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from .exceptions import AuthenticationError, RateLimitError
from .responses import ErrorResponse

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses"""

    def __init__(
        self,
        app: ASGIApp,
        log_level: str = "INFO",
        include_body: bool = False,
        max_body_size: int = 1024,
        exclude_paths: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.log_level = getattr(logging, log_level.upper())
        self.include_body = include_body
        self.max_body_size = max_body_size
        self.exclude_paths = set(exclude_paths or ["/health", "/metrics"])

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details"""

        # Skip logging for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        start_time = time.time()
        request_id = id(request)

        # Log request
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Include request body if enabled
        if self.include_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if len(body) <= self.max_body_size:
                    try:
                        log_data["body"] = json.loads(body) if body else None
                    except json.JSONDecodeError:
                        log_data["body"] = body.decode("utf-8", errors="ignore")
                else:
                    log_data["body"] = f"<truncated: {len(body)} bytes>"
            except Exception as e:
                log_data["body_error"] = str(e)

        logger.log(self.log_level, f"Request started: {log_data}")

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            response_data = {
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "response_headers": dict(response.headers),
            }

            logger.log(self.log_level, f"Request completed: {response_data}")

            return response

        except Exception as e:
            duration = time.time() - start_time
            error_data = {
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": round(duration * 1000, 2),
            }

            logger.error(f"Request failed: {error_data}")
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with configurable limits"""

    def __init__(
        self,
        app: ASGIApp,
        calls_per_minute: int = 60,
        calls_per_hour: int = 1000,
        calls_per_day: int = 10000,
        exclude_paths: Optional[List[str]] = None,
        key_func: Optional[Callable[[Request], str]] = None,
    ):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.calls_per_hour = calls_per_hour
        self.calls_per_day = calls_per_day
        self.exclude_paths = set(exclude_paths or ["/health", "/metrics"])
        self.key_func = key_func or self._default_key_func

        # Storage for rate limit counters
        self.minute_counters: Dict[str, deque] = defaultdict(lambda: deque())
        self.hour_counters: Dict[str, deque] = defaultdict(lambda: deque())
        self.day_counters: Dict[str, deque] = defaultdict(lambda: deque())

        # Cleanup task
        self._cleanup_task = None

    def _default_key_func(self, request: Request) -> str:
        """Default function to extract rate limiting key from request"""
        # Use IP address as default
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting"""

        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        key = self.key_func(request)
        now = time.time()

        # Check rate limits
        if not self._check_rate_limit(key, now):
            return ErrorResponse(
                message="Rate limit exceeded",
                status_code=429,
                error_code="RATE_LIMIT_EXCEEDED",
            ).to_starlette_response()

        # Record the request
        self._record_request(key, now)

        return await call_next(request)

    def _check_rate_limit(self, key: str, now: float) -> bool:
        """Check if request is within rate limits"""

        # Clean old entries and check limits
        return (
            self._check_and_clean_counter(self.minute_counters[key], now, 60, self.calls_per_minute)
            and self._check_and_clean_counter(self.hour_counters[key], now, 3600, self.calls_per_hour)
            and self._check_and_clean_counter(self.day_counters[key], now, 86400, self.calls_per_day)
        )

    def _check_and_clean_counter(self, counter: deque, now: float, window: int, limit: int) -> bool:
        """Check and clean a specific counter"""
        # Remove old entries
        while counter and counter[0] < now - window:
            counter.popleft()

        # Check if under limit
        return len(counter) < limit

    def _record_request(self, key: str, now: float):
        """Record a request in all counters"""
        self.minute_counters[key].append(now)
        self.hour_counters[key].append(now)
        self.day_counters[key].append(now)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """JWT and API key authentication middleware"""

    def __init__(
        self,
        app: ASGIApp,
        secret_key: str,
        algorithm: str = "HS256",
        exclude_paths: Optional[List[str]] = None,
        api_key_header: str = "X-API-Key",
        jwt_header: str = "Authorization",
    ):
        super().__init__(app)
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.exclude_paths = set(exclude_paths or ["/health", "/docs", "/openapi.json"])
        self.api_key_header = api_key_header
        self.jwt_header = jwt_header

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Authenticate request"""

        # Skip authentication for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Try API key authentication first
        api_key = request.headers.get(self.api_key_header)
        if api_key:
            user = await self._authenticate_api_key(api_key)
            if user:
                request.state.user = user
                return await call_next(request)

        # Try JWT authentication
        auth_header = request.headers.get(self.jwt_header)
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            user = await self._authenticate_jwt(token)
            if user:
                request.state.user = user
                return await call_next(request)

        # No valid authentication found
        return ErrorResponse(
            message="Authentication required",
            status_code=401,
            error_code="AUTHENTICATION_REQUIRED",
        ).to_starlette_response()

    async def _authenticate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Authenticate using API key"""
        # This is a placeholder - implement your API key validation logic
        # You might want to check against a database of valid API keys
        if api_key == "test-api-key":
            return {"user_id": "api_user", "type": "api_key"}
        return None

    async def _authenticate_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """Authenticate using JWT token"""
        try:
            from jose import JWTError, jwt

            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("sub")
            if user_id:
                return {"user_id": user_id, "type": "jwt", "claims": payload}

        except (JWTError, ImportError):
            pass

        return None


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware"""

    def __init__(self, app: ASGIApp, debug: bool = False):
        super().__init__(app)
        self.debug = debug

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle exceptions globally"""
        try:
            return await call_next(request)
        except Exception as e:
            return await self._handle_exception(request, e)

    async def _handle_exception(self, request: Request, exc: Exception) -> Response:
        """Handle different types of exceptions"""

        if isinstance(exc, RateLimitError):
            return ErrorResponse(
                message="Rate limit exceeded",
                status_code=429,
                error_code="RATE_LIMIT_EXCEEDED",
            ).to_starlette_response()

        elif isinstance(exc, AuthenticationError):
            return ErrorResponse(
                message="Authentication failed",
                status_code=401,
                error_code="AUTHENTICATION_FAILED",
            ).to_starlette_response()

        else:
            # Log the error
            logger.exception(f"Unhandled exception in {request.method} {request.url}")

            if self.debug:
                import traceback

                return ErrorResponse(
                    message="Internal server error",
                    status_code=500,
                    error_code="INTERNAL_ERROR",
                    details={
                        "error": str(exc),
                        "type": type(exc).__name__,
                        "traceback": traceback.format_exc(),
                    },
                ).to_starlette_response()
            else:
                return ErrorResponse(
                    message="Internal server error",
                    status_code=500,
                    error_code="INTERNAL_ERROR",
                ).to_starlette_response()


class CompressionMiddleware(BaseHTTPMiddleware):
    """Response compression middleware"""

    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 1024,
        compressible_types: Optional[Set[str]] = None,
    ):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compressible_types = compressible_types or {
            "application/json",
            "application/javascript",
            "text/html",
            "text/css",
            "text/plain",
            "text/xml",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Compress response if applicable"""

        # Check if client accepts compression
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding:
            return await call_next(request)

        response = await call_next(request)

        # Check if response should be compressed
        if not self._should_compress(response):
            return response

        # Compress response body
        return await self._compress_response(response)

    def _should_compress(self, response: Response) -> bool:
        """Check if response should be compressed"""

        # Check content type
        content_type = response.headers.get("content-type", "").split(";")[0]
        if content_type not in self.compressible_types:
            return False

        # Check size
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) < self.minimum_size:
            return False

        # Check if already compressed
        if response.headers.get("content-encoding"):
            return False

        return True

    async def _compress_response(self, response: Response) -> Response:
        """Compress response body"""
        import gzip

        # Get response body
        if hasattr(response, "body"):
            body = response.body
        else:
            body = b""

        # Compress body
        compressed_body = gzip.compress(body)

        # Update headers
        response.headers["content-encoding"] = "gzip"
        response.headers["content-length"] = str(len(compressed_body))

        # Create new response with compressed body
        return Response(
            content=compressed_body,
            status_code=response.status_code,
            headers=response.headers,
            media_type=response.media_type,
        )


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting application metrics"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.metrics: Dict[str, Any] = {
            "requests_total": 0,
            "requests_by_method": defaultdict(int),
            "requests_by_status": defaultdict(int),
            "response_times": deque(maxlen=1000),  # Keep last 1000 response times
            "active_requests": 0,
            "errors_total": 0,
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Collect metrics for request"""

        start_time = time.time()
        self.metrics["requests_total"] += 1
        self.metrics["requests_by_method"][request.method] += 1
        self.metrics["active_requests"] += 1

        try:
            response = await call_next(request)

            # Record metrics
            duration = time.time() - start_time
            self.metrics["response_times"].append(duration)
            self.metrics["requests_by_status"][response.status_code] += 1

            if response.status_code >= 400:
                self.metrics["errors_total"] += 1

            return response

        except Exception as e:
            self.metrics["errors_total"] += 1
            raise
        finally:
            self.metrics["active_requests"] -= 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        response_times = list(self.metrics["response_times"])

        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
        else:
            avg_response_time = max_response_time = min_response_time = 0

        return {
            "requests_total": self.metrics["requests_total"],
            "requests_by_method": dict(self.metrics["requests_by_method"]),
            "requests_by_status": dict(self.metrics["requests_by_status"]),
            "active_requests": self.metrics["active_requests"],
            "errors_total": self.metrics["errors_total"],
            "avg_response_time": round(avg_response_time, 4),
            "max_response_time": round(max_response_time, 4),
            "min_response_time": round(min_response_time, 4),
            "error_rate": round(
                self.metrics["errors_total"] / max(self.metrics["requests_total"], 1) * 100,
                2,
            ),
        }


# Middleware factory functions
def create_cors_middleware(app: ASGIApp, **kwargs) -> CORSMiddleware:
    """Create CORS middleware with sensible defaults"""
    config = {
        "allow_origins": ["*"],
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
        **kwargs,
    }
    return CORSMiddleware(app, **config)


def create_rate_limit_middleware(
    calls_per_minute: int = 60, calls_per_hour: int = 1000, **kwargs
) -> RateLimitMiddleware:
    """Create rate limiting middleware with defaults"""
    return RateLimitMiddleware(calls_per_minute=calls_per_minute, calls_per_hour=calls_per_hour, **kwargs)


def create_auth_middleware(secret_key: str, **kwargs) -> AuthenticationMiddleware:
    """Create authentication middleware"""
    return AuthenticationMiddleware(secret_key=secret_key, **kwargs)
