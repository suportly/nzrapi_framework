"""
User service layer - contains business logic
"""

import logging
from typing import List, Optional
from uuid import UUID

from examples.clean_dependency_injection.config import settings
from examples.clean_dependency_injection.models.user import PaginationParams, User, UserCreate, UserResponse, UserUpdate
from examples.clean_dependency_injection.repositories.user_repository import UserRepository


class UserServiceError(Exception):
    """Base exception for user service errors"""

    pass


class MaxUsersReachedError(UserServiceError):
    """Raised when maximum users limit is reached"""

    pass


class UserNotFoundError(UserServiceError):
    """Raised when user is not found"""

    pass


class DuplicateUserError(UserServiceError):
    """Raised when trying to create duplicate user"""

    pass


class UserService:
    """User service containing business logic"""

    def __init__(self, user_repository: UserRepository, logger: logging.Logger):
        self._user_repo = user_repository
        self._logger = logger
        self._settings = settings

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create a new user with business logic validation"""
        self._logger.info(f"Creating user: {user_data.username}")

        # Check max users limit
        current_count = await self._user_repo.count()
        if current_count >= self._settings.app.max_users:
            self._logger.warning(f"Max users limit reached: {current_count}")
            raise MaxUsersReachedError("Maximum users limit reached")

        # Check for duplicate username
        existing_user = await self._user_repo.find_by_username(user_data.username)
        if existing_user:
            self._logger.warning(f"Attempt to create duplicate user: {user_data.username}")
            raise DuplicateUserError(f"User with username '{user_data.username}' already exists")

        # Create user
        user = await self._user_repo.create(user_data)
        self._logger.info(f"User created successfully: {user.username} (ID: {user.id})")

        return UserResponse.from_user(user, "User created successfully")

    async def get_user_by_id(self, user_id: UUID) -> UserResponse:
        """Get user by ID"""
        self._logger.debug(f"Getting user by ID: {user_id}")

        user = await self._user_repo.find_by_id(user_id)
        if not user:
            self._logger.warning(f"User not found: {user_id}")
            raise UserNotFoundError(f"User with ID '{user_id}' not found")

        return UserResponse.from_user(user, "User retrieved successfully")

    async def get_users(self, pagination: PaginationParams) -> dict:
        """Get paginated list of users"""
        self._logger.debug(f"Getting users with pagination: page={pagination.page}, limit={pagination.limit}")

        users = await self._user_repo.find_all(pagination)
        total_count = await self._user_repo.count()

        return {
            "users": [user.model_dump() for user in users],
            "pagination": {
                "page": pagination.page,
                "limit": pagination.limit,
                "total": total_count,
                "has_next": pagination.offset + pagination.limit < total_count,
                "has_prev": pagination.page > 1,
            },
            "message": f"Retrieved {len(users)} users",
        }

    async def update_user(self, user_id: UUID, user_data: UserUpdate) -> UserResponse:
        """Update user"""
        self._logger.info(f"Updating user: {user_id}")

        # Check if user exists
        existing_user = await self._user_repo.find_by_id(user_id)
        if not existing_user:
            raise UserNotFoundError(f"User with ID '{user_id}' not found")

        # Update user
        update_data = user_data.model_dump(exclude_unset=True)
        updated_user = await self._user_repo.update(user_id, update_data)

        if not updated_user:
            raise UserServiceError("Failed to update user")

        self._logger.info(f"User updated successfully: {user_id}")
        return UserResponse.from_user(updated_user, "User updated successfully")

    async def delete_user(self, user_id: UUID) -> dict:
        """Delete user"""
        self._logger.info(f"Deleting user: {user_id}")

        # Check if user exists
        user = await self._user_repo.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User with ID '{user_id}' not found")

        # Delete user
        deleted = await self._user_repo.delete(user_id)
        if not deleted:
            raise UserServiceError("Failed to delete user")

        self._logger.info(f"User deleted successfully: {user_id}")
        return {"message": f"User '{user.username}' deleted successfully", "deleted_user": user.model_dump()}

    async def get_user_statistics(self) -> dict:
        """Get user statistics"""
        total_users = await self._user_repo.count()
        max_users = self._settings.app.max_users

        return {
            "total_users": total_users,
            "max_users": max_users,
            "available_slots": max_users - total_users,
            "usage_percentage": round((total_users / max_users) * 100, 2) if max_users > 0 else 0,
        }
