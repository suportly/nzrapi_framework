"""
{{ project_name }} - AI API Server built with nzrRest Framework
"""

import uvicorn
from config import settings
from models import Base
from views import router as api_router

from nzrrest import NzrRestApp
from nzrrest.middleware import (
    ErrorHandlingMiddleware,
    MetricsMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
)

# Create nzrRest application
app = NzrRestApp(
    database_url=settings.DATABASE_URL,
    debug=settings.DEBUG,
    title="{{ project_name }} API",
    version="1.0.0",
)

# Add middleware
if settings.ENABLE_CORS:
    from starlette.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(ErrorHandlingMiddleware, debug=settings.DEBUG)
app.add_middleware(RequestLoggingMiddleware, log_level="INFO")
app.add_middleware(MetricsMiddleware)

if settings.ENABLE_RATE_LIMITING:
    app.add_middleware(
        RateLimitMiddleware,
        calls_per_minute=settings.RATE_LIMIT_PER_MINUTE,
        calls_per_hour=settings.RATE_LIMIT_PER_HOUR,
    )

# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Add health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "framework": "nzrRest",
        "version": "1.0.0",
        "project": "{{ project_name }}",
    }


# Add metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Get application metrics"""
    # Get metrics from middleware
    for middleware in app.middleware_stack:
        if hasattr(middleware.cls, "get_metrics"):
            return middleware.cls.get_metrics()
    return {"error": "Metrics not available"}


# Startup event to load AI models
@app.on_startup
async def startup_event():
    """Initialize AI models and database"""
    # Load AI models from configuration
    await app.ai_registry.load_models_from_config(settings.AI_MODELS_CONFIG)

    # Create database tables if they don't exist
    if app.db_manager:
        await app.db_manager.create_tables(Base)

    print(f"🚀 {{ project_name }} API server started successfully!")
    print(f"📊 Loaded {len(app.ai_registry.list_models())} AI models")


# Shutdown event
@app.on_shutdown
async def shutdown_event():
    """Cleanup resources"""
    print("🛑 Shutting down {{ project_name }} API server...")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
