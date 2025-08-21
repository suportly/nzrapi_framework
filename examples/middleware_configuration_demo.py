"""
Middleware Configuration Demo

This example demonstrates the clean way to configure middleware
directly in NzrApiApp constructor.

Key features:
1. Clean middleware configuration in constructor
2. Multiple middleware types working together
3. Conditional middleware based on environment
4. Built-in nzrapi middleware showcase
"""

import os

from nzrapi import (
    CORSMiddleware,
    JSONResponse,
    Middleware,
    NzrApiApp,
)
from nzrapi.middleware import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    TimingMiddleware,
)

# Environment configuration
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
ENABLE_RATE_LIMIT = os.getenv("ENABLE_RATE_LIMIT", "false").lower() == "true"
# Use an in-memory SQLite DB by default for demos; override via DATABASE_URL if needed
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")


# --- Clean Middleware Configuration ---
def create_middleware_stack():
    """Create middleware stack based on environment"""

    # Base middleware stack (always enabled)
    middleware = [
        # Add request ID to each request for tracing
        Middleware(RequestIDMiddleware),
        # Add timing headers for performance monitoring
        Middleware(TimingMiddleware),
        # Log all requests (structured logging)
        Middleware(
            LoggingMiddleware,
            log_level="DEBUG" if DEBUG else "INFO",
            include_request_body=DEBUG,
            include_response_body=DEBUG,
        ),
        # Handle errors gracefully
        Middleware(ErrorHandlingMiddleware),
        # CORS for web applications
        Middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
            allow_headers=["*"],
        ),
    ]

    # Conditional middleware based on environment
    if ENABLE_RATE_LIMIT:
        middleware.append(
            Middleware(
                RateLimitMiddleware,
                calls_per_minute=60,
                calls_per_hour=1000,
                calls_per_day=10000,
            )
        )

    return middleware


# --- Application Setup with Clean Middleware Configuration ---
app = NzrApiApp(
    title="🔧 Middleware Configuration Demo",
    description="Demonstrates clean middleware configuration in NzrApiApp constructor",
    version="1.0.0",
    debug=DEBUG,
    database_url=DATABASE_URL,
    # ✨ Clean middleware configuration - just pass the list!
    middleware=create_middleware_stack(),
    docs_url="/docs",
    docs_openapi_url="/openapi.json",
)


# --- Demo Routes ---
@app.get("/")
async def root():
    """Root endpoint showing middleware info"""
    return JSONResponse(
        {
            "title": "🔧 Middleware Configuration Demo",
            "description": "Clean middleware configuration via NzrApiApp constructor",
            "middleware_count": len(app.middleware_stack),
            "middleware_configured": [
                "RequestIDMiddleware - Adds X-Request-ID header",
                "TimingMiddleware - Adds X-Process-Time header",
                "LoggingMiddleware - Structured request/response logging",
                "ErrorHandlingMiddleware - Graceful error handling",
                "CORSMiddleware - Cross-origin resource sharing",
                "RateLimitMiddleware - Request rate limiting (optional)",
            ],
            "benefits": [
                "Clean configuration in constructor",
                "No manual app.add_middleware() calls",
                "Environment-based conditional middleware",
                "All nzrapi middleware ready to use",
            ],
        }
    )


@app.get("/middleware-info")
async def middleware_info():
    """Get detailed middleware information"""
    middleware_info = []

    for i, middleware in enumerate(app.middleware_stack):
        middleware_info.append(
            {
                "index": i,
                "class": middleware.cls.__name__,
                "module": middleware.cls.__module__,
            }
        )

    return JSONResponse(
        {
            "total_middleware": len(app.middleware_stack),
            "middleware_stack": middleware_info,
            "configuration": {
                "debug_mode": DEBUG,
                "rate_limiting_enabled": ENABLE_RATE_LIMIT,
            },
        }
    )


@app.get("/test-timing")
async def test_timing():
    """Test endpoint to see timing middleware in action"""
    import asyncio

    # Simulate some work
    await asyncio.sleep(0.1)

    return JSONResponse(
        {
            "message": "Check the X-Process-Time header!",
            "info": "TimingMiddleware adds processing time to response headers",
            "tip": "Open DevTools -> Network to see the header",
        }
    )


@app.get("/test-error")
async def test_error():
    """Test endpoint to see error handling middleware"""
    # This will trigger ErrorHandlingMiddleware
    raise ValueError("This is a test error to demonstrate ErrorHandlingMiddleware")


@app.get("/test-rate-limit")
async def test_rate_limit():
    """Test endpoint for rate limiting (if enabled)"""
    return JSONResponse(
        {
            "message": "Make multiple requests to test rate limiting",
            "rate_limit_enabled": ENABLE_RATE_LIMIT,
            "tip": "Set ENABLE_RATE_LIMIT=true and make many requests to see rate limiting",
        }
    )


# --- Health Check ---
@app.get("/health")
async def health():
    """Health check endpoint"""
    return JSONResponse(
        {
            "status": "healthy",
            "middleware_configured": len(app.middleware_stack),
            "debug_mode": DEBUG,
            "rate_limiting": ENABLE_RATE_LIMIT,
        }
    )


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Middleware Configuration Demo")
    print("🔧 Key Feature: Clean middleware configuration in NzrApiApp constructor")
    print("")

    # Show configured middleware
    print(f"📋 Configured {len(app.middleware_stack)} middleware:")
    for i, middleware in enumerate(app.middleware_stack, 1):
        print(f"  {i}. {middleware.cls.__name__}")

    print("")
    print("🎯 Benefits achieved:")
    print("  ✅ Clean constructor-based configuration")
    print("  ✅ No manual app.add_middleware() calls needed")
    print("  ✅ Environment-based conditional middleware")
    print("  ✅ All nzrapi middleware ready to use")
    print("")

    print("🔗 Try these endpoints:")
    print("  - GET  / - Middleware overview")
    print("  - GET  /middleware-info - Detailed middleware info")
    print("  - GET  /test-timing - See TimingMiddleware in action")
    print("  - GET  /test-error - See ErrorHandlingMiddleware")
    print("  - GET  /test-rate-limit - Test rate limiting")
    print("")
    print("💡 Environment variables:")
    print(f"  - DEBUG={DEBUG}")
    print(f"  - ENABLE_RATE_LIMIT={ENABLE_RATE_LIMIT}")
    print("")
    print("Visit http://localhost:8000/docs for full API documentation")

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=DEBUG)
