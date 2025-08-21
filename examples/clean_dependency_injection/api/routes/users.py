"""
User routes - clean separation of concerns
"""

from uuid import UUID

from examples.clean_dependency_injection.api.dependencies import LoggerDep, PaginationDep, UserServiceDep
from examples.clean_dependency_injection.models.user import UserCreate, UserUpdate
from examples.clean_dependency_injection.services.user_service import (
    DuplicateUserError,
    MaxUsersReachedError,
    UserNotFoundError,
    UserServiceError,
)
from nzrapi import Path, Router
from nzrapi.responses import JSONResponse

router = Router(prefix="/api/v1/users", tags=["users"])


@router.get("/")
async def list_users(user_service: UserServiceDep, pagination: PaginationDep, logger: LoggerDep):
    """
    List users with pagination

    Clean separation:
    - Route only handles HTTP concerns
    - Business logic in service layer
    - Data access in repository layer
    """
    logger.debug("Handling list users request")

    try:
        result = await user_service.get_users(pagination)
        return JSONResponse(result)

    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return JSONResponse({"error": "Internal server error", "message": str(e)}, status_code=500)


@router.get("/{user_id}")
async def get_user(
    user_id: UUID = Path(description="User ID"), user_service: UserServiceDep = None, logger: LoggerDep = None
):
    """
    Get user by ID

    Demonstrates:
    - Path parameter validation
    - Clean error handling
    - Service layer abstraction
    """
    logger.debug(f"Handling get user request: {user_id}")

    try:
        result = await user_service.get_user_by_id(user_id)
        return JSONResponse(result.model_dump())

    except UserNotFoundError as e:
        logger.warning(f"User not found: {user_id}")
        return JSONResponse({"error": "User not found", "message": str(e)}, status_code=404)
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return JSONResponse({"error": "Internal server error", "message": str(e)}, status_code=500)


@router.post("/")
async def create_user(user_data: UserCreate, user_service: UserServiceDep, logger: LoggerDep):
    """
    Create a new user

    Demonstrates:
    - Request validation via Pydantic
    - Business logic in service layer
    - Proper error handling with specific exceptions
    """
    logger.info(f"Handling create user request: {user_data.username}")

    try:
        result = await user_service.create_user(user_data)
        return JSONResponse(result.model_dump(), status_code=201)

    except MaxUsersReachedError as e:
        logger.warning("Max users limit reached")
        return JSONResponse({"error": "Limit exceeded", "message": str(e)}, status_code=400)
    except DuplicateUserError as e:
        logger.warning(f"Duplicate user attempt: {user_data.username}")
        return JSONResponse({"error": "Duplicate user", "message": str(e)}, status_code=409)
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return JSONResponse({"error": "Internal server error", "message": str(e)}, status_code=500)


@router.patch("/{user_id}")
async def update_user(
    user_id: UUID = Path(description="User ID to update"),
    user_data: UserUpdate = None,
    user_service: UserServiceDep = None,
    logger: LoggerDep = None,
):
    """
    Update user

    Demonstrates:
    - Partial updates with Pydantic
    - Path parameter validation
    - Service layer abstraction
    """
    logger.info(f"Handling update user request: {user_id}")

    try:
        result = await user_service.update_user(user_id, user_data)
        return JSONResponse(result.model_dump())

    except UserNotFoundError as e:
        logger.warning(f"User not found for update: {user_id}")
        return JSONResponse({"error": "User not found", "message": str(e)}, status_code=404)
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        return JSONResponse({"error": "Internal server error", "message": str(e)}, status_code=500)


@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID = Path(description="User ID to delete"), user_service: UserServiceDep = None, logger: LoggerDep = None
):
    """
    Delete user

    Demonstrates:
    - Clean resource deletion
    - Proper error handling
    - Service layer abstraction
    """
    logger.info(f"Handling delete user request: {user_id}")

    try:
        result = await user_service.delete_user(user_id)
        return JSONResponse(result)

    except UserNotFoundError as e:
        logger.warning(f"User not found for deletion: {user_id}")
        return JSONResponse({"error": "User not found", "message": str(e)}, status_code=404)
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return JSONResponse({"error": "Internal server error", "message": str(e)}, status_code=500)


@router.get("/stats/summary")
async def get_user_statistics(user_service: UserServiceDep, logger: LoggerDep):
    """
    Get user statistics

    Demonstrates:
    - Business logic abstraction
    - Statistics endpoint pattern
    """
    logger.debug("Handling user statistics request")

    try:
        stats = await user_service.get_user_statistics()
        return JSONResponse(stats)

    except Exception as e:
        logger.error(f"Error getting user statistics: {e}")
        return JSONResponse({"error": "Internal server error", "message": str(e)}, status_code=500)
