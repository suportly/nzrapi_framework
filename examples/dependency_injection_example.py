"""
Dependency Injection example demonstrating advanced dependency injection in nzrapi
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from nzrapi import check_password_hash  # 🆕 Função simplificada de verificação
from nzrapi import create_password_hash  # 🆕 Função simplificada de hash
from nzrapi import get_session_reliable  # 🆕 Session confiável
from nzrapi import with_db_session  # 🆕 Decorator de session
from nzrapi import (
    Depends,
    NzrApiApp,
    Path,
    Query,
    Router,
    authenticated_user,
    create_dependency_provider,
    get_current_user,
    register_dependency,
    require_auth,
)
from nzrapi.responses import JSONResponse


# Models
class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    username: str
    email: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6)


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(10, ge=1, le=100)
    offset: int = Field(0, ge=0)


# Mock database
users_db: List[User] = []
sessions_db: Dict[str, User] = {}


# Custom dependency functions
async def get_database():
    """Dependency to get database connection (mock)"""
    return {"connected": True, "users": users_db}


async def get_settings():
    """Dependency to get application settings"""
    return {"app_name": "Dependency Injection Demo", "version": "1.0.0", "max_users": 1000}


def get_pagination_params_custom(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
) -> PaginationParams:
    """Custom pagination dependency"""
    offset = (page - 1) * limit
    return PaginationParams(page=page, limit=limit, offset=offset)


async def get_current_user_from_header(request) -> Optional[User]:
    """Get current user from authorization header"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]  # Remove "Bearer "
    return sessions_db.get(token)


def require_admin_user(current_user: User = Depends(get_current_user_from_header)) -> User:
    """Dependency that requires admin user"""
    if not current_user:
        from nzrapi.exceptions import AuthenticationError

        raise AuthenticationError("Authentication required")

    # Check if user is admin (mock check)
    if current_user.username != "admin":
        from nzrapi.exceptions import PermissionDenied

        raise PermissionDenied("Admin access required")

    return current_user


# Service layer with dependencies
class UserService:
    """User service with dependency injection"""

    def __init__(self, database: dict, settings: dict):
        self.database = database
        self.settings = settings

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user"""
        if len(self.database["users"]) >= self.settings["max_users"]:
            raise ValueError("Maximum users limit reached")

        new_user = User(username=user_data.username, email=user_data.email)
        self.database["users"].append(new_user)
        return new_user

    async def get_users(self, pagination: PaginationParams) -> List[User]:
        """Get paginated users"""
        users = self.database["users"]
        return users[pagination.offset : pagination.offset + pagination.limit]

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        return next((u for u in self.database["users"] if u.id == user_id), None)


async def get_user_service(
    database: dict = Depends(get_database), settings: dict = Depends(get_settings)
) -> UserService:
    """Dependency to get user service with injected dependencies"""
    return UserService(database, settings)


# Create app and router with improved debugging
app = NzrApiApp(
    title="Dependency Injection Demo",
    version="1.0.0",
    debug=True,
    debug_level="debug",  # 🆕 Debug para dependency injection
)
router = Router(prefix="/api/v1", tags=["users"])


# Routes with dependency injection
@router.get("/users")
async def list_users(
    user_service: UserService = Depends(get_user_service),
    pagination: PaginationParams = Depends(get_pagination_params_custom),
    current_user: Optional[User] = Depends(get_current_user_from_header),
):
    """
    List users with pagination

    Demonstrates:
    - Service dependency injection
    - Custom pagination dependency
    - Optional authentication dependency
    """
    users = await user_service.get_users(pagination)

    return JSONResponse(
        {
            "users": [user.dict() for user in users],
            "pagination": {
                "page": pagination.page,
                "limit": pagination.limit,
                "total": len(user_service.database["users"]),
            },
            "authenticated_user": current_user.username if current_user else None,
        }
    )


@router.get("/users/{user_id}")
async def get_user(user_id: UUID = Path(description="User ID"), user_service: UserService = Depends(get_user_service)):
    """
    Get user by ID

    Demonstrates:
    - Path parameter validation
    - Service dependency injection
    """
    user = await user_service.get_user_by_id(user_id)

    if not user:
        from nzrapi.responses import ErrorResponse

        return ErrorResponse(message="User not found", status_code=404, details={"user_id": str(user_id)})

    return JSONResponse({"user": user.dict()})


@router.post("/users")
async def create_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service),
    current_user: Optional[User] = Depends(get_current_user_from_header),
):
    """
    Create a new user

    Demonstrates:
    - Request body validation
    - Service dependency injection
    - Optional authentication
    """
    try:
        new_user = await user_service.create_user(user_data)

        return JSONResponse(
            {
                "user": new_user.dict(),
                "message": "User created successfully",
                "created_by": current_user.username if current_user else "anonymous",
            },
            status_code=201,
        )

    except ValueError as e:
        from nzrapi.responses import ErrorResponse

        return ErrorResponse(message=str(e), status_code=400)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID = Path(description="User ID to delete"),
    admin_user: User = Depends(require_admin_user),
    user_service: UserService = Depends(get_user_service),
):
    """
    Delete a user (admin only)

    Demonstrates:
    - Required authentication dependency
    - Admin role dependency
    - Cascading dependencies
    """
    user = await user_service.get_user_by_id(user_id)

    if not user:
        from nzrapi.responses import ErrorResponse

        return ErrorResponse(message="User not found", status_code=404)

    # Remove user from database
    user_service.database["users"] = [u for u in user_service.database["users"] if u.id != user_id]

    return JSONResponse(
        {
            "message": f"User {user.username} deleted successfully",
            "deleted_by": admin_user.username,
            "deleted_user": user.dict(),
        }
    )


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user_from_header)):
    """
    Get current user information

    Demonstrates:
    - Authentication dependency
    - User information retrieval
    """
    if not current_user:
        from nzrapi.responses import ErrorResponse

        return ErrorResponse(message="Authentication required", status_code=401)

    return JSONResponse({"user": current_user.dict(), "message": "Current user information"})


@router.get("/stats")
async def get_stats(
    settings: dict = Depends(get_settings),
    database: dict = Depends(get_database),
    admin_user: User = Depends(require_admin_user),
):
    """
    Get application statistics (admin only)

    Demonstrates:
    - Multiple simple dependencies
    - Configuration injection
    - Admin-only endpoint
    """
    return JSONResponse(
        {
            "app_name": settings["app_name"],
            "version": settings["version"],
            "total_users": len(database["users"]),
            "max_users": settings["max_users"],
            "active_sessions": len(sessions_db),
            "requested_by": admin_user.username,
        }
    )


# Example of dependency with sub-dependencies
class CacheService:
    """Mock cache service"""

    def __init__(self, settings: dict):
        self.settings = settings
        self.cache = {}

    async def get(self, key: str):
        return self.cache.get(key)

    async def set(self, key: str, value: any, ttl: int = 300):
        self.cache[key] = value
        return True


async def get_cache_service(settings: dict = Depends(get_settings)) -> CacheService:
    """Cache service with settings dependency"""
    return CacheService(settings)


@router.get("/cached-data/{key}")
async def get_cached_data(key: str = Path(description="Cache key"), cache: CacheService = Depends(get_cache_service)):
    """
    Get cached data

    Demonstrates:
    - Dependency with sub-dependencies
    - Service composition
    """
    value = await cache.get(key)

    if value is None:
        # Set some mock data
        mock_data = {"key": key, "timestamp": datetime.utcnow().isoformat()}
        await cache.set(key, mock_data)
        value = mock_data

    return JSONResponse({"key": key, "value": value, "cache_size": len(cache.cache)})


# Login endpoint to create sessions for testing
@router.post("/login")
async def login(username: str = Query(..., description="Username"), password: str = Query(..., description="Password")):
    """
    Simple login for testing dependencies
    """
    # Mock authentication
    user = next((u for u in users_db if u.username == username), None)

    if not user or password != "password123":  # Mock password check
        from nzrapi.responses import ErrorResponse

        return ErrorResponse(message="Invalid credentials", status_code=401)

    # Create session token
    token = str(uuid4())
    sessions_db[token] = user

    return JSONResponse({"token": token, "user": user.dict(), "message": "Login successful"})


# Add sample data on startup
@app.on_startup
async def populate_sample_data():
    """Add sample users and admin for testing"""
    admin_user = User(username="admin", email="admin@example.com")
    regular_user = User(username="john", email="john@example.com")

    users_db.extend([admin_user, regular_user])

    print("🚀 Dependency Injection demo started!")
    print("📚 Sample users created:")
    print("  - admin (admin@example.com)")
    print("  - john (john@example.com)")
    print("\n🔐 To test authentication:")
    print("  1. POST /api/v1/login?username=admin&password=password123")
    print("  2. Use the returned token in Authorization: Bearer <token>")
    print("\n🔗 Try these endpoints:")
    print("  - GET /api/v1/users (public)")
    print("  - GET /api/v1/me (requires auth)")
    print("  - GET /api/v1/stats (requires admin)")
    print("  - DELETE /api/v1/users/{id} (requires admin)")


# Include router
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    print("Starting Dependency Injection Demo...")
    print("Visit http://localhost:8000/docs for interactive documentation")

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
