"""
Middleware system for NzrApi framework
"""

import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Union

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from .exceptions import AuthenticationError, RateLimitError
from .responses import ErrorResponse

logger = logging.getLogger(__name__)


def parse_rate_limit(rate_limit_str: str) -> dict:
    """Parse rate limit string into a dictionary of limits.

    Example input: "1000/day, 100/hour, 10/minute"
    Returns: {"day": 1000, "hour": 100, "minute": 10}

    Args:
        rate_limit_str: String containing rate limits in format "value/period"

    Returns:
        Dictionary with parsed rate limits

    Examples:
        >>> parse_rate_limit("1000/day, 100/hour")
        {"day": 1000, "hour": 100}

        >>> parse_rate_limit("50/min, 1000/hour, 10000/day")
        {"minute": 50, "hour": 1000, "day": 10000}
    """
    limits = {}
    for part in rate_limit_str.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            value_str, period = part.split("/")
            value = int(value_str.strip())
            period = period.strip().lower()
            if period in ["min", "minute", "minutes"]:
                limits["minute"] = value
            elif period in ["hour", "hours"]:
                limits["hour"] = value
            elif period in ["day", "days"]:
                limits["day"] = value
        except (ValueError, AttributeError):
            continue
    return limits


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
        calls_per_minute: Union[int, str] = 60,
        calls_per_hour: Union[int, str] = 1000,
        calls_per_day: Union[int, str] = 10000,
        exclude_paths: Optional[List[str]] = None,
        key_func: Optional[Callable[[Request], str]] = None,
        rate_limit: Optional[Union[str, Dict[str, int]]] = None,
    ):
        super().__init__(app)
        # Parse flexible rate limit configuration
        m, h, d = self._normalize_limits(calls_per_minute, calls_per_hour, calls_per_day, rate_limit)
        self.calls_per_minute = m
        self.calls_per_hour = h
        self.calls_per_day = d
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

    @staticmethod
    def _normalize_limits(
        calls_per_minute: Union[int, str],
        calls_per_hour: Union[int, str],
        calls_per_day: Union[int, str],
        rate_limit: Optional[Union[str, Dict[str, int]]],
    ) -> tuple[int, int, int]:
        """Normalize various rate limit inputs into integers for minute/hour/day.

        Supports:
        - Separate integer parameters
        - A single string like "1000/day, 100/hour, 10/minute" (also accepts d/h/m aliases)
        - A dict like {"day": 1000, "hour": 100, "minute": 10}
        - Misconfigured case where a string is passed into calls_per_minute
        """
        # Defaults
        m, h, d = 60, 1000, 10000

        def parse_string(s: str) -> tuple[int, int, int]:
            s = s.strip()
            if not s:
                return m, h, d
            parts = [p.strip() for p in s.replace(";", ",").split(",") if p.strip()]
            mm, hh, dd = m, h, d
            for p in parts:
                # e.g., "10/minute" or "10 m" or "10 per minute"
                token = p.lower().replace("per ", "/").replace(" ", "/")
                # split by '/'
                try:
                    amount_str, unit = token.split("/", 1)
                    amount = int(amount_str)
                except Exception:
                    # If only a number is given, assume per minute
                    try:
                        amount = int(token)
                        unit = "minute"
                    except Exception:
                        continue
                unit = unit.strip()
                if unit in {"m", "min", "minute", "minutes"}:
                    mm = amount
                elif unit in {"h", "hr", "hour", "hours"}:
                    hh = amount
                elif unit in {"d", "day", "days"}:
                    dd = amount
            return mm, hh, dd

        if isinstance(rate_limit, dict):
            m = int(rate_limit.get("minute", m))
            h = int(rate_limit.get("hour", h))
            d = int(rate_limit.get("day", d))
            return m, h, d
        elif isinstance(rate_limit, str):
            return parse_string(rate_limit)

        # Handle strings passed into individual params
        if isinstance(calls_per_minute, str) or isinstance(calls_per_hour, str) or isinstance(calls_per_day, str):
            # If any param is a string, try to parse a combined format from the minute param
            base = (
                calls_per_minute
                if isinstance(calls_per_minute, str)
                else (calls_per_hour if isinstance(calls_per_hour, str) else calls_per_day)
            )
            mm, hh, dd = parse_string(str(base))
            return mm, hh, dd

        # Fallback to provided integers
        return int(calls_per_minute), int(calls_per_hour), int(calls_per_day)

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
            )

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
        )

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
            )

        elif isinstance(exc, AuthenticationError):
            return ErrorResponse(
                message="Authentication failed",
                status_code=401,
                error_code="AUTHENTICATION_FAILED",
            )

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
                )
            else:
                return ErrorResponse(
                    message="Internal server error",
                    status_code=500,
                    error_code="INTERNAL_ERROR",
                )


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


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds a unique request ID to each request.

    The request ID can be used for tracing requests across services.
    """

    def __init__(
        self,
        app: ASGIApp,
        header_name: str = "X-Request-ID",
        id_gen: Callable[[], str] = None,
    ):
        super().__init__(app)
        self.header_name = header_name
        self.id_gen = id_gen or (lambda: str(uuid.uuid4()))

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and add a request ID if not present."""
        # Get request ID from headers or generate a new one
        request_id = request.headers.get(self.header_name) or self.id_gen()

        # Add request ID to request state
        request.state.request_id = request_id

        # Process the request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers[self.header_name] = request_id

        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware that adds X-Process-Time header to responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Log request
        logger.info(
            "Request started",
            extra={
                "request": {
                    "method": request.method,
                    "url": str(request.url),
                    "headers": dict(request.headers),
                    "client": request.client.host if request.client else None,
                },
                "request_id": getattr(request.state, "request_id", None),
            },
        )

        try:
            response = await call_next(request)

            # Log response
            logger.info(
                "Request completed",
                extra={
                    "request_id": getattr(request.state, "request_id", None),
                    "response": {
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                    },
                },
            )

            return response

        except Exception as e:
            logger.exception(
                "Request failed",
                extra={
                    "request_id": getattr(request.state, "request_id", None),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise


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
    calls_per_minute: Union[int, str] = 60,
    calls_per_hour: Union[int, str] = 1000,
    calls_per_day: Union[int, str] = 10000,
    rate_limit: Optional[Union[str, Dict[str, int]]] = None,
    **kwargs,
) -> RateLimitMiddleware:
    """Create rate limiting middleware with defaults and flexible input formats."""
    return RateLimitMiddleware(
        calls_per_minute=calls_per_minute,
        calls_per_hour=calls_per_hour,
        calls_per_day=calls_per_day,
        rate_limit=rate_limit,
        **kwargs,
    )


def create_auth_middleware(secret_key: str, **kwargs) -> AuthenticationMiddleware:
    """Create authentication middleware"""
    return AuthenticationMiddleware(secret_key=secret_key, **kwargs)
