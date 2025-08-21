"""
Security schemes and utilities for NzrApi framework
"""

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union

from .dependencies import Depends
from .exceptions import AuthenticationError, ValidationError
from .requests import Request


class SecurityBase:
    """Base class for security schemes"""

    def __init__(self, description: Optional[str] = None):
        self.description = description
        self.scheme_name: Optional[str] = None

    def __call__(self, request: Request):
        """Called when used as a dependency"""
        raise NotImplementedError


class HTTPBase(SecurityBase):
    """Base class for HTTP authentication schemes"""

    def __init__(self, *, scheme: str, description: Optional[str] = None, auto_error: bool = True):
        super().__init__(description=description)
        self.scheme = scheme
        self.auto_error = auto_error

    def get_openapi_security_scheme(self) -> Dict[str, Any]:
        """Get OpenAPI security scheme definition"""
        return {"type": "http", "scheme": self.scheme, "description": self.description}


class HTTPBasic(HTTPBase):
    """HTTP Basic authentication scheme"""

    def __init__(self, *, realm: Optional[str] = None, description: Optional[str] = None, auto_error: bool = True):
        super().__init__(scheme="basic", description=description, auto_error=auto_error)
        self.realm = realm

    def __call__(self, request: Request) -> Optional[Dict[str, str]]:
        """Extract HTTP Basic credentials"""
        authorization = request.headers.get("Authorization")

        if not authorization:
            if self.auto_error:
                raise AuthenticationError(
                    "Not authenticated",
                    headers={"WWW-Authenticate": "Basic" + (f' realm="{self.realm}"' if self.realm else "")},
                )
            return None

        try:
            scheme, credentials = authorization.split(" ", 1)
            if scheme.lower() != "basic":
                if self.auto_error:
                    raise AuthenticationError("Invalid authentication credentials")
                return None

            decoded = base64.b64decode(credentials).decode("utf-8")
            username, password = decoded.split(":", 1)

            return {"username": username, "password": password}

        except (ValueError, UnicodeDecodeError):
            if self.auto_error:
                raise AuthenticationError("Invalid authentication credentials")
            return None


class HTTPBearer(HTTPBase):
    """HTTP Bearer token authentication scheme"""

    def __init__(
        self, *, bearerFormat: Optional[str] = None, description: Optional[str] = None, auto_error: bool = True
    ):
        super().__init__(scheme="bearer", description=description, auto_error=auto_error)
        self.bearer_format = bearerFormat

    def get_openapi_security_scheme(self) -> Dict[str, Any]:
        scheme = super().get_openapi_security_scheme()
        if self.bearer_format:
            scheme["bearerFormat"] = self.bearer_format
        return scheme

    def __call__(self, request: Request) -> Optional[str]:
        """Extract Bearer token"""
        authorization = request.headers.get("Authorization")

        if not authorization:
            if self.auto_error:
                raise AuthenticationError("Not authenticated", headers={"WWW-Authenticate": "Bearer"})
            return None

        try:
            scheme, token = authorization.split(" ", 1)
            if scheme.lower() != "bearer":
                if self.auto_error:
                    raise AuthenticationError("Invalid authentication credentials")
                return None

            return token

        except ValueError:
            if self.auto_error:
                raise AuthenticationError("Invalid authentication credentials")
            return None


class HTTPDigest(HTTPBase):
    """HTTP Digest authentication scheme"""

    def __init__(self, *, description: Optional[str] = None, auto_error: bool = True):
        super().__init__(scheme="digest", description=description, auto_error=auto_error)

    def __call__(self, request: Request) -> Optional[Dict[str, str]]:
        """Extract HTTP Digest credentials"""
        authorization = request.headers.get("Authorization")

        if not authorization:
            if self.auto_error:
                raise AuthenticationError("Not authenticated", headers={"WWW-Authenticate": "Digest"})
            return None

        try:
            scheme, credentials = authorization.split(" ", 1)
            if scheme.lower() != "digest":
                if self.auto_error:
                    raise AuthenticationError("Invalid authentication credentials")
                return None

            # Parse digest parameters
            params = {}
            for item in credentials.split(", "):
                key, value = item.split("=", 1)
                params[key] = value.strip('"')

            return params

        except (ValueError, AttributeError):
            if self.auto_error:
                raise AuthenticationError("Invalid authentication credentials")
            return None


class APIKeyBase(SecurityBase):
    """Base class for API Key authentication schemes"""

    def __init__(self, *, name: str, description: Optional[str] = None, auto_error: bool = True):
        super().__init__(description=description)
        self.name = name
        self.auto_error = auto_error


class APIKeyQuery(APIKeyBase):
    """API Key in query parameter authentication"""

    def __init__(self, *, name: str, description: Optional[str] = None, auto_error: bool = True):
        super().__init__(name=name, description=description, auto_error=auto_error)

    def get_openapi_security_scheme(self) -> Dict[str, Any]:
        return {"type": "apiKey", "name": self.name, "in": "query", "description": self.description}

    def __call__(self, request: Request) -> Optional[str]:
        """Extract API key from query parameters"""
        api_key = request.query_params.get(self.name)

        if not api_key:
            if self.auto_error:
                raise AuthenticationError("Not authenticated")
            return None

        return api_key


class APIKeyHeader(APIKeyBase):
    """API Key in header authentication"""

    def __init__(self, *, name: str = "X-API-Key", description: Optional[str] = None, auto_error: bool = True):
        super().__init__(name=name, description=description, auto_error=auto_error)

    def get_openapi_security_scheme(self) -> Dict[str, Any]:
        return {"type": "apiKey", "name": self.name, "in": "header", "description": self.description}

    def __call__(self, request: Request) -> Optional[str]:
        """Extract API key from headers"""
        api_key = request.headers.get(self.name)

        if not api_key:
            if self.auto_error:
                raise AuthenticationError("Not authenticated")
            return None

        return api_key


class APIKeyCookie(APIKeyBase):
    """API Key in cookie authentication"""

    def __init__(self, *, name: str, description: Optional[str] = None, auto_error: bool = True):
        super().__init__(name=name, description=description, auto_error=auto_error)

    def get_openapi_security_scheme(self) -> Dict[str, Any]:
        return {"type": "apiKey", "name": self.name, "in": "cookie", "description": self.description}

    def __call__(self, request: Request) -> Optional[str]:
        """Extract API key from cookies"""
        api_key = request.cookies.get(self.name)

        if not api_key:
            if self.auto_error:
                raise AuthenticationError("Not authenticated")
            return None

        return api_key


class OAuth2:
    """OAuth2 authentication scheme"""

    def __init__(self, *, flows: Dict[str, Any], description: Optional[str] = None, auto_error: bool = True):
        self.flows = flows
        self.description = description
        self.auto_error = auto_error
        self.scheme_name: Optional[str] = None

    def get_openapi_security_scheme(self) -> Dict[str, Any]:
        return {"type": "oauth2", "flows": self.flows, "description": self.description}

    def __call__(self, request: Request) -> Optional[str]:
        """Extract OAuth2 token from Authorization header"""
        authorization = request.headers.get("Authorization")

        if not authorization:
            if self.auto_error:
                raise AuthenticationError("Not authenticated", headers={"WWW-Authenticate": "Bearer"})
            return None

        try:
            scheme, token = authorization.split(" ", 1)
            if scheme.lower() != "bearer":
                if self.auto_error:
                    raise AuthenticationError("Invalid authentication credentials")
                return None

            return token

        except ValueError:
            if self.auto_error:
                raise AuthenticationError("Invalid authentication credentials")
            return None


class OAuth2PasswordBearer(OAuth2):
    """OAuth2 password bearer flow"""

    def __init__(
        self,
        tokenUrl: str,
        *,
        scheme_name: Optional[str] = None,
        scopes: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        auto_error: bool = True,
    ):
        flows: Dict[str, Dict[str, Any]] = {"password": {"tokenUrl": tokenUrl}}
        if scopes is not None:
            flows["password"]["scopes"] = scopes

        super().__init__(flows=flows, description=description, auto_error=auto_error)
        self.scheme_name = scheme_name


class OAuth2AuthorizationCodeBearer(OAuth2):
    """OAuth2 authorization code bearer flow"""

    def __init__(
        self,
        authorizationUrl: str,
        tokenUrl: str,
        *,
        scheme_name: Optional[str] = None,
        scopes: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        auto_error: bool = True,
    ):
        flows: Dict[str, Dict[str, Any]] = {
            "authorizationCode": {"authorizationUrl": authorizationUrl, "tokenUrl": tokenUrl}
        }
        if scopes is not None:
            flows["authorizationCode"]["scopes"] = scopes

        super().__init__(flows=flows, description=description, auto_error=auto_error)
        self.scheme_name = scheme_name


# JWT Token utilities
class JWTBearer(HTTPBearer):
    """JWT Bearer token authentication with validation"""

    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str = "HS256",
        verify_expiration: bool = True,
        description: Optional[str] = None,
        auto_error: bool = True,
    ):
        super().__init__(bearerFormat="JWT", description=description, auto_error=auto_error)
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.verify_expiration = verify_expiration

    def __call__(self, request: Request) -> Optional[str]:
        """Extract and validate JWT token. Returns the token string if valid.

        This keeps the return type compatible with HTTPBearer.__call__ (str | None)
        while still performing validation using decode_token().
        """
        token = super().__call__(request)

        if not token:
            return None

        try:
            # Validate token, but return the token string
            self.decode_token(token)
            return token

        except Exception as e:
            if self.auto_error:
                raise AuthenticationError(f"Invalid token: {str(e)}")
            return None

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate JWT token"""
        try:
            import jwt

            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": self.verify_expiration}
            )

            return payload

        except ImportError:
            raise RuntimeError("PyJWT is required for JWT token validation. Install with: pip install PyJWT")
        except Exception as e:
            raise AuthenticationError(f"Token validation failed: {str(e)}")

    def create_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT token"""
        try:
            import jwt

            to_encode = data.copy()

            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(hours=24)

            to_encode.update({"exp": expire})

            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt

        except ImportError:
            raise RuntimeError("PyJWT is required for JWT token creation. Install with: pip install PyJWT")


# Security utilities
def generate_secret_key(length: int = 32) -> str:
    """Generate a random secret key"""
    return secrets.token_urlsafe(length)


def hash_password(password: str, salt: Optional[str] = None) -> tuple:
    """Hash a password with salt"""
    if salt is None:
        salt = secrets.token_hex(16)

    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)

    return base64.b64encode(hashed).decode("utf-8"), salt


def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """Verify a password against its hash"""
    test_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(test_hash, hashed_password)


def create_access_token(
    data: Dict[str, Any], secret_key: str, expires_delta: Optional[timedelta] = None, algorithm: str = "HS256"
) -> str:
    """Create an access token"""
    jwt_bearer = JWTBearer(secret_key=secret_key, algorithm=algorithm)
    return jwt_bearer.create_token(data, expires_delta)


def verify_token(token: str, secret_key: str, algorithm: str = "HS256") -> Dict[str, Any]:
    """Verify and decode a token"""
    jwt_bearer = JWTBearer(secret_key=secret_key, algorithm=algorithm)
    return jwt_bearer.decode_token(token)


# Common security scheme instances
basic_auth = HTTPBasic()
bearer_token = HTTPBearer()
api_key_query = APIKeyQuery(name="api_key")
api_key_header = APIKeyHeader(name="X-API-Key")
api_key_cookie = APIKeyCookie(name="access_token")


# Security dependency factories
def create_jwt_bearer(secret_key: str, **kwargs) -> JWTBearer:
    """Create a JWT Bearer security scheme"""
    return JWTBearer(secret_key=secret_key, **kwargs)


def create_jwt_payload_dependency(secret_key: str, **kwargs) -> Callable:
    """Create a dependency that validates a JWT and returns its decoded payload.

    Usage:
        jwt_payload = Depends(create_jwt_payload_dependency("secret"))
    """
    bearer = JWTBearer(secret_key=secret_key, **kwargs)

    def dependency(token: Any = Depends(bearer)) -> Dict[str, Any]:
        if not token:
            raise AuthenticationError("Authentication required")
        return bearer.decode_token(token)

    return dependency


def create_oauth2_password_bearer(token_url: str, **kwargs) -> OAuth2PasswordBearer:
    """Create an OAuth2 password bearer scheme"""
    return OAuth2PasswordBearer(tokenUrl=token_url, **kwargs)


def create_basic_auth_dependency(verify_credentials: Callable) -> Callable:
    """Create a basic auth dependency with credential verification"""

    def basic_auth_dependency(credentials: Any = Depends(basic_auth)) -> str:
        if not credentials:
            raise AuthenticationError("Authentication required")

        if not verify_credentials(credentials["username"], credentials["password"]):
            raise AuthenticationError("Invalid credentials")

        return credentials["username"]

    return basic_auth_dependency


def create_api_key_dependency(verify_api_key: Callable) -> Callable:
    """Create an API key dependency with key verification"""

    def api_key_dependency(api_key: Any = Depends(api_key_header)):
        if not api_key:
            raise AuthenticationError("API key required")

        user = verify_api_key(api_key)
        if not user:
            raise AuthenticationError("Invalid API key")

        return user

    return api_key_dependency
