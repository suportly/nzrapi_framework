"""
User repository implementations
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from examples.clean_dependency_injection.models.user import PaginationParams, User, UserCreate


class UserRepository(ABC):
    """Abstract user repository"""

    @abstractmethod
    async def create(self, user_data: UserCreate) -> User:
        """Create a new user"""
        pass

    @abstractmethod
    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        """Find user by ID"""
        pass

    @abstractmethod
    async def find_by_username(self, username: str) -> Optional[User]:
        """Find user by username"""
        pass

    @abstractmethod
    async def find_all(self, pagination: PaginationParams) -> List[User]:
        """Find all users with pagination"""
        pass

    @abstractmethod
    async def update(self, user_id: UUID, user_data: dict) -> Optional[User]:
        """Update user"""
        pass

    @abstractmethod
    async def delete(self, user_id: UUID) -> bool:
        """Delete user"""
        pass

    @abstractmethod
    async def count(self) -> int:
        """Count total users"""
        pass


class InMemoryUserRepository(UserRepository):
    """In-memory user repository implementation"""

    def __init__(self):
        self._users: List[User] = []

    async def create(self, user_data: UserCreate) -> User:
        """Create a new user"""
        user = User(username=user_data.username, email=user_data.email)
        self._users.append(user)
        return user

    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        """Find user by ID"""
        return next((u for u in self._users if u.id == user_id), None)

    async def find_by_username(self, username: str) -> Optional[User]:
        """Find user by username"""
        return next((u for u in self._users if u.username == username), None)

    async def find_all(self, pagination: PaginationParams) -> List[User]:
        """Find all users with pagination"""
        start = pagination.offset
        end = start + pagination.limit
        return self._users[start:end]

    async def update(self, user_id: UUID, user_data: dict) -> Optional[User]:
        """Update user"""
        user = await self.find_by_id(user_id)
        if not user:
            return None

        # Update user fields
        for field, value in user_data.items():
            if hasattr(user, field) and value is not None:
                setattr(user, field, value)

        return user

    async def delete(self, user_id: UUID) -> bool:
        """Delete user"""
        user = await self.find_by_id(user_id)
        if user:
            self._users.remove(user)
            return True
        return False

    async def count(self) -> int:
        """Count total users"""
        return len(self._users)
