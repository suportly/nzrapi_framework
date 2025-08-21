"""
Example demonstrating the advanced type safety features in nzrapi
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from nzrapi import NzrApiApp, Router
from nzrapi.responses import JSONResponse
from nzrapi.typing import Path, Query


# Pydantic models for request/response
class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="User's name")
    email: str = Field(..., description="User's email address")
    age: Optional[int] = Field(None, ge=0, le=150, description="User's age")
    tags: List[str] = Field(default_factory=list, description="User tags")


class User(BaseModel):
    id: UUID = Field(default_factory=uuid4, description="User ID")
    name: str = Field(..., description="User's name")
    email: str = Field(..., description="User's email address")
    age: Optional[int] = Field(None, description="User's age")
    tags: List[str] = Field(default_factory=list, description="User tags")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")


class UserResponse(BaseModel):
    user: User
    message: str = "User operation successful"


class UserListResponse(BaseModel):
    users: List[User]
    total: int
    page: int
    limit: int


# In-memory storage for demo
users_db: List[User] = []


# Create app and router
app = NzrApiApp(title="Typed API Demo", version="1.0.0")
router = Router(prefix="/api/v1", tags=["users"])


@router.post("/users", response_model=UserResponse)
async def create_user(request, user_data: UserCreate) -> UserResponse:
    """
    Create a new user with automatic validation

    This endpoint demonstrates:
    - Automatic request body validation using Pydantic
    - Type safety for parameters
    - Response model definition
    """
    new_user = User(name=user_data.name, email=user_data.email, age=user_data.age, tags=user_data.tags)
    users_db.append(new_user)

    return JSONResponse({"user": new_user.dict(), "message": f"User {new_user.name} created successfully"})


@router.get("/users", response_model=UserListResponse)
async def list_users(
    request,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    name_filter: Optional[str] = Query(None, description="Filter by name"),
) -> UserListResponse:
    """
    List users with pagination and filtering

    This endpoint demonstrates:
    - Query parameter validation with constraints
    - Optional parameters with defaults
    - Complex response models
    """
    # Apply name filter if provided
    filtered_users = users_db
    if name_filter:
        filtered_users = [u for u in users_db if name_filter.lower() in u.name.lower()]

    # Apply pagination
    start = (page - 1) * limit
    end = start + limit
    paginated_users = filtered_users[start:end]

    return JSONResponse(
        {"users": [user.dict() for user in paginated_users], "total": len(filtered_users), "page": page, "limit": limit}
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(request, user_id: UUID = Path(description="User ID to retrieve")) -> UserResponse:
    """
    Get a specific user by ID

    This endpoint demonstrates:
    - Path parameter validation with UUID type
    - Automatic type conversion
    - Error handling for not found
    """
    user = next((u for u in users_db if u.id == user_id), None)
    if not user:
        from nzrapi.responses import ErrorResponse

        return ErrorResponse(message="User not found", status_code=404, details={"user_id": str(user_id)})

    return JSONResponse({"user": user.dict(), "message": "User retrieved successfully"})


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    request, user_id: UUID = Path(description="User ID to update"), user_data: UserCreate = None
) -> UserResponse:
    """
    Update an existing user

    This endpoint demonstrates:
    - Combination of path parameters and request body
    - Type validation for both
    """
    user_idx = next((i for i, u in enumerate(users_db) if u.id == user_id), None)
    if user_idx is None:
        from nzrapi.responses import ErrorResponse

        return ErrorResponse(message="User not found", status_code=404, details={"user_id": str(user_id)})

    # Update user
    existing_user = users_db[user_idx]
    updated_user = User(
        id=existing_user.id,
        created_at=existing_user.created_at,
        name=user_data.name,
        email=user_data.email,
        age=user_data.age,
        tags=user_data.tags,
    )
    users_db[user_idx] = updated_user

    return JSONResponse({"user": updated_user.dict(), "message": f"User {updated_user.name} updated successfully"})


@router.delete("/users/{user_id}")
async def delete_user(request, user_id: UUID = Path(description="User ID to delete")):
    """
    Delete a user

    This endpoint demonstrates:
    - Simple path parameter validation
    - No response model (returns simple JSON)
    """
    user_idx = next((i for i, u in enumerate(users_db) if u.id == user_id), None)
    if user_idx is None:
        from nzrapi.responses import ErrorResponse

        return ErrorResponse(message="User not found", status_code=404, details={"user_id": str(user_id)})

    deleted_user = users_db.pop(user_idx)
    return JSONResponse({"message": f"User {deleted_user.name} deleted successfully", "deleted_user_id": str(user_id)})


# Health check endpoint without type validation for comparison
@router.get("/health", auto_validate=False)
async def health_check(request):
    """
    Simple health check without automatic validation
    """
    return JSONResponse({"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "users_count": len(users_db)})


# Add some sample data
@app.on_startup
async def populate_sample_data():
    """Add some sample users for testing"""
    sample_users = [
        User(name="Alice Johnson", email="alice@example.com", age=28, tags=["developer", "python"]),
        User(name="Bob Smith", email="bob@example.com", age=35, tags=["manager", "agile"]),
        User(name="Carol Williams", email="carol@example.com", age=24, tags=["designer", "ui/ux"]),
    ]
    users_db.extend(sample_users)
    print(f"Added {len(sample_users)} sample users")


# Include router in app
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    print("Starting Typed API Demo...")
    print("Visit http://localhost:8000/docs for interactive documentation")
    print("\nExample requests you can try:")
    print("GET /api/v1/users?page=1&limit=5")
    print("GET /api/v1/users?name_filter=alice")
    print("POST /api/v1/users with JSON body")

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
