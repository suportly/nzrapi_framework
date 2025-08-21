"""
Advanced dependency injection system for NzrApi framework
"""

import asyncio
import inspect
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, get_type_hints

from .requests import Request

T = TypeVar("T")


class Depends:
    """Dependency marker for dependency injection"""

    def __init__(self, dependency: Callable, *, use_cache: bool = True):
        self.dependency = dependency
        self.use_cache = use_cache


def get_request() -> Request:
    """Dependency to get current request object"""
    # This will be resolved by the dependency injector
    pass


def get_db_session():
    """Dependency to get database session from app"""
    # This will be resolved by the dependency injector
    pass


def get_current_user():
    """Dependency to get current authenticated user"""
    # This will be resolved by the dependency injector
    pass


class DependencyInjector:
    """Advanced dependency injection system"""

    def __init__(self):
        self.dependency_cache: Dict[str, Any] = {}
        self.resolving: set = set()  # Track circular dependencies

    async def solve_dependencies(
        self, func: Callable, request: Request, path_params: Dict[str, Any], app_instance: Any = None
    ) -> Dict[str, Any]:
        """Resolve all dependencies for a function"""

        signature = inspect.signature(func)
        type_hints = get_type_hints(func)
        resolved_dependencies = {}

        for param_name, param in signature.parameters.items():
            # Skip 'self' and 'request' if they're not dependency-injected
            if param_name in ("self", "cls"):
                continue

            # Handle explicit request parameter
            if param_name == "request" and not isinstance(param.default, Depends):
                resolved_dependencies[param_name] = request
                continue

            # Handle path parameters
            if param_name in path_params:
                resolved_dependencies[param_name] = path_params[param_name]
                continue

            # Handle dependency injection
            if isinstance(param.default, Depends):
                dependency_value = await self._resolve_dependency(param.default, request, app_instance, param_name)
                resolved_dependencies[param_name] = dependency_value
                continue

            # Handle built-in dependencies by name
            if param_name in self._get_builtin_dependencies():
                dependency_value = await self._resolve_builtin_dependency(param_name, request, app_instance)
                resolved_dependencies[param_name] = dependency_value
                continue

            # Check for type-based dependency resolution
            annotation = type_hints.get(param_name, param.annotation)
            if annotation and annotation != inspect.Parameter.empty:
                dependency_value = await self._resolve_type_dependency(annotation, request, app_instance, param_name)
                if dependency_value is not None:
                    resolved_dependencies[param_name] = dependency_value
                    continue

            # Use default value if available
            if param.default != inspect.Parameter.empty:
                resolved_dependencies[param_name] = param.default

        return resolved_dependencies

    async def _resolve_dependency(self, depends: Depends, request: Request, app_instance: Any, param_name: str) -> Any:
        """Resolve a specific dependency"""

        dependency_func = depends.dependency
        cache_key = f"{dependency_func.__module__}.{dependency_func.__name__}_{id(request)}"

        # Check cache if enabled
        if depends.use_cache and cache_key in self.dependency_cache:
            return self.dependency_cache[cache_key]

        # Prevent circular dependencies
        if cache_key in self.resolving:
            raise RuntimeError(f"Circular dependency detected for {dependency_func.__name__}")

        self.resolving.add(cache_key)

        try:
            # Resolve sub-dependencies recursively
            sub_dependencies = await self.solve_dependencies(dependency_func, request, {}, app_instance)

            # Call the dependency function
            if inspect.iscoroutinefunction(dependency_func):
                result = await dependency_func(**sub_dependencies)
            else:
                result = dependency_func(**sub_dependencies)

            # Cache if enabled
            if depends.use_cache:
                self.dependency_cache[cache_key] = result

            return result

        finally:
            self.resolving.discard(cache_key)

    async def _resolve_builtin_dependency(self, param_name: str, request: Request, app_instance: Any) -> Any:
        """Resolve built-in dependencies by parameter name"""

        if param_name == "request":
            return request

        elif param_name == "db_session" or param_name == "session":
            if app_instance and hasattr(app_instance, "get_db_session"):
                async with app_instance.get_db_session() as session:
                    return session
            return None

        elif param_name == "current_user" or param_name == "user":
            # Get user from request state (set by authentication middleware)
            return getattr(request.state, "user", None)

        elif param_name == "app":
            return app_instance

        elif param_name == "ai_registry":
            if app_instance and hasattr(app_instance, "ai_registry"):
                return app_instance.ai_registry
            return None

        return None

    async def _resolve_type_dependency(
        self, annotation: Type, request: Request, app_instance: Any, param_name: str
    ) -> Optional[Any]:
        """Resolve dependency based on type annotation"""

        # Handle Request type
        if annotation == Request or (inspect.isclass(annotation) and issubclass(annotation, Request)):
            return request

        # Handle database session types
        if hasattr(annotation, "__name__") and "session" in annotation.__name__.lower():
            if app_instance and hasattr(app_instance, "get_db_session"):
                async with app_instance.get_db_session() as session:
                    return session

        # Handle custom dependency types registered in app
        if app_instance and hasattr(app_instance, "dependency_providers"):
            provider = app_instance.dependency_providers.get(annotation)
            if provider:
                if inspect.iscoroutinefunction(provider):
                    return await provider(request)
                else:
                    return provider(request)

        return None

    def _get_builtin_dependencies(self) -> List[str]:
        """Get list of built-in dependency parameter names"""
        return ["request", "db_session", "session", "current_user", "user", "app", "ai_registry"]

    def clear_cache(self):
        """Clear the dependency cache"""
        self.dependency_cache.clear()


# Global dependency injector instance
default_injector = DependencyInjector()


def inject_dependencies(func: Callable) -> Callable:
    """Decorator to enable dependency injection for a function"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Find request object in args or kwargs
        request = None
        app_instance = None

        # Look for request in args (assuming it's typically the first or second arg)
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break

        # Look for request in kwargs
        if not request:
            request = kwargs.get("request")

        if not request:
            raise RuntimeError("No request object found for dependency injection")

        # Get app instance from request state
        app_instance = getattr(request.state, "nzrapi_app", None)

        # Resolve dependencies
        dependencies = await default_injector.solve_dependencies(func, request, kwargs.copy(), app_instance)

        # Merge with existing kwargs, giving priority to dependencies
        final_kwargs = {**kwargs, **dependencies}

        # Call original function
        if inspect.iscoroutinefunction(func):
            return await func(*args, **final_kwargs)
        else:
            return func(*args, **final_kwargs)

    # Preserve original function reference for schema generation, even if already wrapped
    setattr(wrapper, "_original_func", getattr(func, "_original_func", func))
    # Marker to indicate this handler uses dependency injection
    setattr(wrapper, "_uses_dependency_injection", True)
    return wrapper


# Common dependency functions
async def get_pagination_params(page: int = 1, limit: int = 10, max_limit: int = 100) -> Dict[str, int]:
    """Dependency for pagination parameters"""
    limit = min(limit, max_limit)
    offset = (page - 1) * limit
    return {"page": page, "limit": limit, "offset": offset}


async def get_authenticated_user(request: Request) -> Optional[Dict[str, Any]]:
    """Dependency for authenticated user"""
    return getattr(request.state, "user", None)


async def require_authentication(request: Request) -> Dict[str, Any]:
    """Dependency that requires authentication"""
    user = getattr(request.state, "user", None)
    if not user:
        from .exceptions import AuthenticationError

        raise AuthenticationError("Authentication required")
    return user


class DatabaseDependency:
    """Database session dependency class"""

    def __init__(self, autocommit: bool = False):
        self.autocommit = autocommit

    async def __call__(self, request: Request):
        app = getattr(request.state, "nzrapi_app", None)
        if not app or not hasattr(app, "get_db_session"):
            raise RuntimeError("Database not configured")

        async with app.get_db_session() as session:
            try:
                yield session
                if self.autocommit:
                    await session.commit()
            except Exception:
                await session.rollback()
                raise


# Common dependency instances
get_db = DatabaseDependency(autocommit=False)
get_db_with_commit = DatabaseDependency(autocommit=True)
pagination = Depends(get_pagination_params)
authenticated_user = Depends(get_authenticated_user)
require_auth = Depends(require_authentication)


# Utility functions for registering custom dependencies
def register_dependency(app_instance, dependency_type: Type, provider: Callable):
    """Register a custom dependency provider"""
    if not hasattr(app_instance, "dependency_providers"):
        app_instance.dependency_providers = {}
    app_instance.dependency_providers[dependency_type] = provider


def create_dependency_provider(provider_func: Callable) -> Callable:
    """Create a dependency provider function"""

    def dependency_provider(request: Request):
        app = getattr(request.state, "nzrapi_app", None)
        return provider_func(request, app)

    return dependency_provider
