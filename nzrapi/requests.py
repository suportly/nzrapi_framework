"""
Enhanced Request class for NzrApi framework
"""

import json
from typing import Any, Dict, Optional, Union
from urllib.parse import parse_qs

from starlette.requests import Request as StarletteRequest


class AnonymousUser:
    """Lightweight anonymous user representation.

    Provides attributes commonly checked by permission classes without
    requiring Starlette's AuthenticationMiddleware to be installed.
    """

    def __init__(self):
        self.is_authenticated: bool = False
        self.id: Optional[Any] = None
        self.role: Optional[str] = None


class Request:
    """Enhanced request class with additional functionality for AI APIs"""

    def __init__(self, request: StarletteRequest):
        self._request = request
        self._json_cache: Optional[Dict[str, Any]] = None

    @property
    def method(self) -> str:
        """HTTP method"""
        return self._request.method

    @property
    def url(self) -> str:
        """Request URL"""
        return str(self._request.url)

    @property
    def headers(self) -> Dict[str, str]:
        """Request headers"""
        return dict(self._request.headers)

    @property
    def path_params(self) -> Dict[str, Any]:
        """Path parameters"""
        return self._request.path_params

    @property
    def query_params(self) -> Dict[str, str]:
        """Query parameters"""
        return dict(self._request.query_params)

    @property
    def client_ip(self) -> Optional[str]:
        """Client IP address"""
        if self._request.client:
            return self._request.client.host
        return None

    @property
    def user_agent(self) -> Optional[str]:
        """User agent string"""
        return self.headers.get("user-agent")

    @property
    def content_type(self) -> Optional[str]:
        """Content type header"""
        return self.headers.get("content-type")

    @property
    def app(self):
        """Access to the application instance"""
        return self._request.app

    async def body(self) -> bytes:
        """Request body as bytes"""
        return await self._request.body()

    async def text(self) -> str:
        """Request body as text"""
        body = await self.body()
        return body.decode("utf-8")

    async def json(self) -> Dict[str, Any]:
        """Request body parsed as JSON"""
        if self._json_cache is None:
            try:
                text = await self.text()
                self._json_cache = json.loads(text) if text else {}
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._json_cache = {}
        return self._json_cache

    async def form(self) -> Dict[str, Any]:
        """Request body parsed as form data"""
        form = await self._request.form()
        return dict(form)

    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get header value with default"""
        return self.headers.get(name.lower(), default)

    def get_query_param(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get query parameter with default"""
        return self.query_params.get(name, default)

    def is_authenticated(self) -> bool:
        """Check if request is authenticated"""
        return hasattr(self, "user") and self.user is not None

    @property
    def user(self) -> Any:
        """Return the authenticated user if available, else an anonymous user.

        Preference order:
        1. User set by our middleware at `request.state.user`.
        2. User provided by Starlette's AuthenticationMiddleware (if present).
        3. Fallback to AnonymousUser instance.
        """
        # 1) Prefer user set by our middleware
        state_user = getattr(self._request.state, "user", None)
        if state_user is not None:
            return state_user

        # 2) Try Starlette's AuthenticationMiddleware if available, avoid assertion
        try:
            if "user" in self._request.scope:
                return getattr(self._request, "user")
        except Exception:
            # If Starlette asserts or any error occurs, fall back to anonymous
            pass

        # 3) Anonymous fallback
        return AnonymousUser()

    def __getattr__(self, name: str) -> Any:
        """Delegate to underlying Starlette request"""
        return getattr(self._request, name)
