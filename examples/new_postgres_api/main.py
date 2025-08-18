import uvicorn
from starlette.authentication import AuthCredentials, SimpleUser
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import Request

from nzrapi import NzrApiApp
from nzrapi.db.models import Model

from . import models  # noqa: F401, ensures models are registered
from .routes import router


# --- Authentication Backend (for demonstration) ---
class BasicAuthBackend:
    async def authenticate(self, conn):
        # In a real app, you'd check headers, tokens, etc.
        # For this example, we'll just return a dummy user.
        return AuthCredentials(["authenticated"]), SimpleUser("dummy_user")


# --- Database Configuration ---
DATABASE_URL = "postgresql+asyncpg://n8n:xjoA531Gs24zKUwXRMdc@localhost:5432/fanboost"

# --- Application Setup ---
app = NzrApiApp(
    title="NzrApi Refactored API",
    version="2.0.0",
    debug=True,
    database_url=DATABASE_URL,
    middleware=[Middleware(AuthenticationMiddleware, backend=BasicAuthBackend())],
)


# Include the API routes
app.include_router(router, prefix="/api")


# --- Startup Event ---
@app.on_startup
async def startup():
    """Create database tables on application startup."""
    async with app.db_manager.engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)


# --- Runnable Main Block ---
if __name__ == "__main__":
    print("Starting NzrApi Refactored PostgreSQL API Example...")
    print(f"API Docs available at http://localhost:8004{app.docs_url}")
    uvicorn.run(app, host="0.0.0.0", port=8004, log_level="info")
