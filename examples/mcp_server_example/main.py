"""
mcp_server_example - AI API Server built with NzrApi Framework
"""

import uvicorn
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from nzrapi import NzrApiApp
from nzrapi.middleware import (
    ErrorHandlingMiddleware,
    MetricsMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
)

from .config import AI_MODELS_CONFIG, settings
from .models import Base
from .views import router as api_router

# Load environment variables from .env file
load_dotenv()


# Create NzrApi application
app = NzrApiApp(
    database_url=settings.DATABASE_URL,
    debug=settings.DEBUG,
    title="mcp_server_example API",
    version="1.0.0",
)

# Add middleware
if settings.ENABLE_CORS:
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
        "framework": "NzrApi",
        "version": "1.0.0",
        "project": "mcp_server_example",
    }


# Add metrics endpoint
@app.get("/metrics")
async def get_metrics(request: Request):
    """Get application metrics"""
    if hasattr(request.app.state, "metrics_middleware"):
        metrics = request.app.state.metrics_middleware.get_metrics()
        return JSONResponse(content=metrics)
    return JSONResponse(content={"error": "Metrics not available"}, status_code=404)


# Startup event to load AI models
@app.on_startup
async def startup_event():
    """Initialize AI models and database"""
    # Find and store the MetricsMiddleware instance in the app state
    current_app = app.app.middleware_stack
    while hasattr(current_app, "app"):
        if isinstance(current_app, MetricsMiddleware):
            app.app.state.metrics_middleware = current_app
            break
        current_app = current_app.app

    # Load AI models from configuration
    await app.ai_registry.load_models_from_config(AI_MODELS_CONFIG)

    # Create database tables if they don't exist
    if app.db_manager:
        await app.db_manager.create_tables(Base)

    print(f"🚀 mcp_server_example API server started successfully!")
    print(f"📊 Loaded {len(app.ai_registry.list_models())} AI models")


# Shutdown event
@app.on_shutdown
async def shutdown_event():
    """Cleanup resources"""
    print("🛑 Shutting down mcp_server_example API server...")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
