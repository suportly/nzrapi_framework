"""
Permission classes for NzrApi framework
"""

from starlette.requests import Request


class BasePermission:
    """Base class for all permission classes."""

    async def has_permission(self, request: Request, view) -> bool:
        """Return `True` if permission is granted, `False` otherwise."""
        return True


class AllowAny(BasePermission):
    """Allow any access."""

    async def has_permission(self, request: Request, view) -> bool:
        return True


class IsAuthenticated(BasePermission):
    """Allows access only to authenticated users."""

    async def has_permission(self, request: Request, view) -> bool:
        return request.user is not None and request.user.is_authenticated


class IsAdminUser(BasePermission):
    """Allows access only to admin users."""

    async def has_permission(self, request: Request, view) -> bool:
        return (
            request.user is not None
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "admin"
        )


class IsAuthenticatedOrReadOnly(BasePermission):
    """Allows authenticated users full access, or read-only for unauthenticated."""

    async def has_permission(self, request: Request, view) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return request.user is not None and request.user.is_authenticated


# HTTP methods considered safe (read-only)
SAFE_METHODS = ("GET", "HEAD", "OPTIONS")
