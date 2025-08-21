"""
Dependency injection setup for the application
"""

import logging
from typing import Annotated

from examples.clean_dependency_injection.config import settings
from examples.clean_dependency_injection.models.user import PaginationParams
from examples.clean_dependency_injection.repositories.user_repository import InMemoryUserRepository, UserRepository
from examples.clean_dependency_injection.services.user_service import UserService
from nzrapi import Depends


# Logger dependency
def get_logger() -> logging.Logger:
    """Get configured logger"""
    logging.basicConfig(
        level=logging.INFO if not settings.debug else logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger("clean_di_example")


# Repository dependency
def get_user_repository() -> UserRepository:
    """Get user repository instance"""
    return InMemoryUserRepository()


# Service dependency
def get_user_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    logger: Annotated[logging.Logger, Depends(get_logger)],
) -> UserService:
    """Get user service with injected dependencies"""
    return UserService(user_repo, logger)


# Pagination dependency
def get_pagination_params(page: int = 1, limit: int = 10) -> PaginationParams:
    """Get pagination parameters"""
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 10

    return PaginationParams(page=page, limit=limit)


# Type aliases for cleaner route signatures
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
LoggerDep = Annotated[logging.Logger, Depends(get_logger)]
PaginationDep = Annotated[PaginationParams, Depends(get_pagination_params)]
