import functools
from typing import Any, Callable, Dict, List, Optional

from .app import NzrApiApp
from .requests import Request


def docs(
    summary: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    request_body: Optional[Dict[str, Any]] = None,
    responses: Optional[Dict[str, Any]] = None,
) -> Callable:
    """
    Decorator to add OpenAPI documentation to an endpoint.
    """

    def decorator(func: Callable) -> Callable:
        func._openapi_docs = {  # type: ignore[attr-defined]
            "summary": summary,
            "description": description,
            "tags": tags,
            "request_body": request_body,
            "responses": responses,
        }
        return func

    return decorator


def transactional(func: Callable) -> Callable:
    """
    Decorator to provide a transactional database session to an endpoint.

    It injects a `session` keyword argument into the decorated function.
    The transaction is automatically committed if the function succeeds,
    or rolled back if it raises an exception.
    """

    @functools.wraps(func)
    async def wrapper(self, request: Request, *args, **kwargs):
        if not hasattr(request.app.state, "nzrapi_app"):
            raise RuntimeError("NzrApiApp not found in request state.")

        app: NzrApiApp = request.app.state.nzrapi_app

        if not app.db_manager:
            raise RuntimeError("Database is not configured. Please provide a `database_url` when creating NzrApiApp.")

        async with app.get_db_session() as session:
            async with session.begin():
                kwargs["session"] = session
                return await func(self, request, *args, **kwargs)

    return wrapper
