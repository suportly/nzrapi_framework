import os
import secrets
import sys
from datetime import timedelta
from typing import Any, Dict, Optional

import uvicorn
from dotenv import load_dotenv
from sqlalchemy import text

# Import models to ensure they are registered with SQLAlchemy
import examples.new_postgres_api.models as models  # noqa: F401
from examples.new_postgres_api.models import User, UserRole
from examples.new_postgres_api.routes import router
from nzrapi import CORSMiddleware, Middleware, NzrApiApp, Request, parse_rate_limit
from nzrapi.db.models import Model
from nzrapi.middleware import (
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    TimingMiddleware,
)
from nzrapi.security import JWTBearer

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/nzrapi_example")

# JWT Configuration
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# CORS Configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

# Parse rate limits from environment (use high defaults to prevent test throttling)
rate_limits = parse_rate_limit(os.getenv("RATE_LIMIT", "100000/day, 10000/hour, 1000/minute"))

# --- Middleware ---
TESTING = os.getenv("PYTEST_CURRENT_TEST") is not None or os.getenv("TESTING") == "1" or "pytest" in sys.modules
ENABLE_RATELIMIT = os.getenv("ENABLE_RATELIMIT", "0") in {"1", "true", "True"}

middleware = [
    # Add request ID to each request for tracing
    Middleware(RequestIDMiddleware),
    # Add timing headers
    Middleware(TimingMiddleware),
    # Log all requests
    Middleware(LoggingMiddleware),
]

if not TESTING and ENABLE_RATELIMIT:
    # Rate limiting with parsed values (disabled during tests)
    middleware.append(
        Middleware(
            RateLimitMiddleware,
            calls_per_minute=rate_limits.get("minute", 60),
            calls_per_hour=rate_limits.get("hour", 1000),
            calls_per_day=rate_limits.get("day", 10000),
        )
    )

# CORS middleware
middleware.append(
    Middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
)

# Note: JWT Authentication is handled via security dependencies, not middleware

# --- Application Setup ---
app = NzrApiApp(
    title="NzrApi Example API",
    version="0.3.0",
    debug=DEBUG,
    database_url=DATABASE_URL,
    middleware=middleware,
    docs_url="/docs",
    docs_openapi_url="/openapi.json",
)

# Include the API routes
app.include_router(router, prefix="/api")


# --- Event Handlers ---


@app.on_startup
async def startup():
    """Initialize application services on startup."""
    # Expose secret key on the Starlette app state for JWT operations
    # Handle case where NzrApiApp.app returns a middleware wrapper without .state
    _asgi_app = app.app
    _state = getattr(_asgi_app, "state", None)
    if _state is None:
        inner_app = getattr(_asgi_app, "app", None)
        _state = getattr(inner_app, "state", None)
    if _state is not None:
        _state.secret_key = SECRET_KEY

    # Drop and recreate database tables to ensure schema is current
    async with app.db_manager.engine.begin() as conn:
        await conn.run_sync(Model.metadata.drop_all)
        await conn.run_sync(Model.metadata.create_all)

    # Create default admin user if none exists
    await create_default_admin()


async def create_default_admin():
    """Create a default admin user if no users exist."""

    async with app.db_manager.get_session() as session:
        # Check if any users exist
        result = await session.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()

        if count == 0:
            # Create default admin user directly
            admin = User(username="admin", email="admin@example.com", full_name="Administrator", role=UserRole.ADMIN)
            admin.set_password("admin123")

            session.add(admin)
            await session.commit()
            print("\n" + "=" * 50)
            print("DEFAULT ADMIN CREDENTIALS")
            print("Username: admin")
            print("Password: admin123")
            print("=" * 50 + "\n")


@app.on_shutdown
async def shutdown():
    """Clean up resources on shutdown."""
    await app.db_manager.dispose()


# --- Main Execution ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NzrApi Example Application")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    print("\n" + "=" * 50)
    print(f"Starting NzrApi Example Application (v{app.version})")
    print(f"Environment: {'Development' if DEBUG else 'Production'}")
    print(f"Database: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
    print(f"API Docs: http://{args.host}:{args.port}/docs")
    print("=" * 50 + "\n")

    uvicorn.run(
        "__main__:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="debug" if DEBUG else "info",
    )
