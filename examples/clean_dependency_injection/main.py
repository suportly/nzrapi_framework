"""
Clean Dependency Injection Example - Refactored with Clean Architecture principles

This example demonstrates:
1. ✅ Separation of Concerns - Each layer has a single responsibility
2. ✅ Dependency Injection - Proper DI with abstractions
3. ✅ Clean Architecture - Domain, Service, Repository, API layers
4. ✅ Error Handling - Structured error handling with custom exceptions
5. ✅ Configuration Management - Centralized configuration
6. ✅ Logging - Structured logging throughout
7. ✅ Type Safety - Full type hints and Pydantic models

Architecture:
- Domain Layer: models/user.py - Business entities
- Repository Layer: repositories/ - Data access abstractions
- Service Layer: services/ - Business logic
- API Layer: api/routes/ - HTTP handling only
- Configuration: config.py - Centralized settings
"""

import logging

from examples.clean_dependency_injection.api.routes.users import router as users_router
from examples.clean_dependency_injection.config import settings
from nzrapi import NzrApiApp

# Create app
app = NzrApiApp(
    title="Clean Dependency Injection Demo",
    description="Refactored example showing Clean Architecture principles",
    version=settings.app.version,
    debug=settings.debug,
)

# Include routers
app.include_router(users_router)


@app.on_startup
async def startup_event():
    """Application startup - seed with sample data"""
    logger = logging.getLogger("clean_di_example")
    logger.info("🚀 Clean Dependency Injection Demo starting up!")

    # Import here to avoid circular imports
    from examples.clean_dependency_injection.api.dependencies import get_logger, get_user_repository, get_user_service
    from examples.clean_dependency_injection.models.user import UserCreate

    # Get dependencies
    user_repo = get_user_repository()
    app_logger = get_logger()
    user_service = get_user_service(user_repo, app_logger)

    # Seed with sample data
    sample_users = [
        UserCreate(username="alice", email="alice@example.com", password="password123"),
        UserCreate(username="bob", email="bob@example.com", password="password123"),
        UserCreate(username="charlie", email="charlie@example.com", password="password123"),
    ]

    for user_data in sample_users:
        try:
            await user_service.create_user(user_data)
        except Exception as e:
            logger.warning(f"Could not create sample user {user_data.username}: {e}")

    logger.info("📚 Sample data created!")
    logger.info("🔗 Available endpoints:")
    logger.info("  - GET  /api/v1/users - List users")
    logger.info("  - POST /api/v1/users - Create user")
    logger.info("  - GET  /api/v1/users/{id} - Get user by ID")
    logger.info("  - PATCH /api/v1/users/{id} - Update user")
    logger.info("  - DELETE /api/v1/users/{id} - Delete user")
    logger.info("  - GET  /api/v1/users/stats/summary - User statistics")
    logger.info("🎯 Visit http://localhost:8000/docs for interactive documentation")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "app": settings.app.name, "version": settings.app.version, "debug": settings.debug}


if __name__ == "__main__":
    import uvicorn

    print("Starting Clean Dependency Injection Demo...")
    print("🏗️ Architecture Improvements Implemented:")
    print("  ✅ Separation of Concerns")
    print("  ✅ Clean Architecture (Domain/Service/Repository/API)")
    print("  ✅ Proper Dependency Injection")
    print("  ✅ Configuration Management")
    print("  ✅ Structured Error Handling")
    print("  ✅ Comprehensive Logging")
    print("  ✅ Type Safety")
    print("")
    print("Visit http://localhost:8000/docs for interactive documentation")

    uvicorn.run(
        "examples.clean_dependency_injection.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
