"""
User domain models
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class User(BaseModel):
    """User domain model"""

    id: UUID = Field(default_factory=uuid4)
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., description="User email address")
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserCreate(BaseModel):
    """User creation data"""

    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    """User update data"""

    email: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """User response model"""

    user: User
    message: str = "Operation successful"

    @classmethod
    def from_user(cls, user: User, message: str = "Operation successful") -> "UserResponse":
        """Create response from user"""
        return cls(user=user, message=message)


class PaginationParams(BaseModel):
    """Pagination parameters"""

    page: int = Field(1, ge=1)
    limit: int = Field(10, ge=1, le=100)
    offset: int = Field(0, ge=0)

    def __init__(self, page: int = 1, limit: int = 10, **kwargs):
        offset = (page - 1) * limit
        super().__init__(page=page, limit=limit, offset=offset, **kwargs)
