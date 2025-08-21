"""
Security example demonstrating various authentication schemes in nzrapi
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from nzrapi import (
    APIKeyHeader,
    Depends,
    HTTPBasic,
    HTTPBearer,
    JWTBearer,
    NzrApiApp,
    OAuth2PasswordBearer,
    Path,
    Query,
    Router,
    create_access_token,
    generate_secret_key,
    hash_password,
    verify_password,
)
from nzrapi.exceptions import AuthenticationError
from nzrapi.responses import JSONResponse


# Models
class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    username: str
    email: str
    is_active: bool = True
    scopes: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class LoginRequest(BaseModel):
    username: str
    password: str


# Mock database
users_db: Dict[str, Dict] = {}
api_keys_db: Dict[str, UUID] = {}
tokens_db: Dict[str, Dict] = {}

# Security configuration
SECRET_KEY = generate_secret_key()
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# Create app
app = NzrApiApp(title="Security Demo API", version="1.0.0")


# Security scheme instances
basic_auth = HTTPBasic()
bearer_auth = HTTPBearer()
jwt_auth = JWTBearer(secret_key=SECRET_KEY, algorithm=JWT_ALGORITHM)
api_key_auth = APIKeyHeader(name="X-API-Key")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Authentication functions
def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate user with username and password"""
    user_data = users_db.get(username)
    if not user_data:
        return None

    if not verify_password(password, user_data["password_hash"], user_data["salt"]):
        return None

    return User(**user_data["user_info"])


def get_user_by_token(token: str) -> Optional[User]:
    """Get user from JWT token"""
    try:
        payload = jwt_auth.decode_token(token)
        username = payload.get("sub")
        if username:
            user_data = users_db.get(username)
            if user_data:
                return User(**user_data["user_info"])
    except Exception:
        pass

    return None


def get_user_by_api_key(api_key: str) -> Optional[User]:
    """Get user from API key"""
    user_id = api_keys_db.get(api_key)
    if not user_id:
        return None

    # Find user by ID
    for user_data in users_db.values():
        if user_data["user_info"]["id"] == str(user_id):
            return User(**user_data["user_info"])

    return None


# Dependency functions
async def get_current_user_basic(credentials: Optional[Dict[str, str]] = Depends(basic_auth)) -> User:
    """Get current user from HTTP Basic auth"""
    if not credentials:
        raise AuthenticationError("Authentication required")

    user = authenticate_user(credentials["username"], credentials["password"])
    if not user:
        raise AuthenticationError("Invalid credentials")

    return user


async def get_current_user_bearer(token: Optional[str] = Depends(bearer_auth)) -> User:
    """Get current user from Bearer token"""
    if not token:
        raise AuthenticationError("Authentication required")

    user = get_user_by_token(token)
    if not user:
        raise AuthenticationError("Invalid token")

    return user


async def get_current_user_jwt(payload: Optional[Dict] = Depends(jwt_auth)) -> User:
    """Get current user from JWT token"""
    if not payload:
        raise AuthenticationError("Authentication required")

    username = payload.get("sub")
    if not username:
        raise AuthenticationError("Invalid token")

    user_data = users_db.get(username)
    if not user_data:
        raise AuthenticationError("User not found")

    return User(**user_data["user_info"])


async def get_current_user_api_key(api_key: Optional[str] = Depends(api_key_auth)) -> User:
    """Get current user from API key"""
    if not api_key:
        raise AuthenticationError("API key required")

    user = get_user_by_api_key(api_key)
    if not user:
        raise AuthenticationError("Invalid API key")

    return user


async def get_current_user_oauth2(token: Optional[str] = Depends(oauth2_scheme)) -> User:
    """Get current user from OAuth2 token"""
    if not token:
        raise AuthenticationError("Authentication required")

    user = get_user_by_token(token)
    if not user:
        raise AuthenticationError("Invalid token")

    return user


def require_scope(required_scope: str):
    """Dependency factory for requiring specific scopes"""

    def scope_dependency(current_user: User = Depends(get_current_user_jwt)):
        if required_scope not in current_user.scopes:
            raise AuthenticationError(f"Scope '{required_scope}' required")
        return current_user

    return scope_dependency


# Routes
router = Router(prefix="/api/v1")


@app.post("/register")
async def register_user(
    username: str = Query(..., min_length=3, max_length=50),
    email: str = Query(...),
    password: str = Query(..., min_length=6),
):
    """Register a new user"""
    if username in users_db:
        from nzrapi.responses import ErrorResponse

        return ErrorResponse(message="Username already exists", status_code=400)

    # Hash password
    password_hash, salt = hash_password(password)

    # Create user
    user = User(username=username, email=email, scopes=["read", "write"])

    # Store in database
    users_db[username] = {"user_info": user.dict(), "password_hash": password_hash, "salt": salt}

    # Create API key for the user
    api_key = generate_secret_key()
    api_keys_db[api_key] = user.id

    return JSONResponse(
        {"message": "User registered successfully", "user": user.dict(), "api_key": api_key}, status_code=201
    )


@app.post("/token")
async def login_for_access_token(login_data: LoginRequest) -> Token:
    """OAuth2 compatible token endpoint"""
    user = authenticate_user(login_data.username, login_data.password)

    if not user:
        raise AuthenticationError("Invalid credentials")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {"sub": user.username, "scopes": user.scopes, "user_id": str(user.id)}

    access_token = create_access_token(
        data=token_data, secret_key=SECRET_KEY, expires_delta=access_token_expires, algorithm=JWT_ALGORITHM
    )

    # Store token info
    tokens_db[access_token] = {"user_id": str(user.id), "expires_at": datetime.utcnow() + access_token_expires}

    return Token(access_token=access_token, expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60)


# Public endpoints
@router.get("/public")
async def public_endpoint():
    """Public endpoint that doesn't require authentication"""
    return JSONResponse(
        {"message": "This is a public endpoint", "timestamp": datetime.utcnow().isoformat(), "access": "public"}
    )


# HTTP Basic Authentication
@router.get("/basic-auth")
async def basic_auth_endpoint(current_user: User = Depends(get_current_user_basic)):
    """Endpoint protected by HTTP Basic authentication"""
    return JSONResponse(
        {"message": "Access granted via HTTP Basic auth", "user": current_user.username, "auth_method": "basic"}
    )


# Bearer Token Authentication
@router.get("/bearer-auth")
async def bearer_auth_endpoint(current_user: User = Depends(get_current_user_bearer)):
    """Endpoint protected by Bearer token authentication"""
    return JSONResponse(
        {"message": "Access granted via Bearer token", "user": current_user.username, "auth_method": "bearer"}
    )


# JWT Authentication
@router.get("/jwt-auth")
async def jwt_auth_endpoint(current_user: User = Depends(get_current_user_jwt)):
    """Endpoint protected by JWT authentication"""
    return JSONResponse(
        {
            "message": "Access granted via JWT token",
            "user": current_user.username,
            "scopes": current_user.scopes,
            "auth_method": "jwt",
        }
    )


# API Key Authentication
@router.get("/api-key-auth")
async def api_key_auth_endpoint(current_user: User = Depends(get_current_user_api_key)):
    """Endpoint protected by API Key authentication"""
    return JSONResponse(
        {"message": "Access granted via API Key", "user": current_user.username, "auth_method": "api_key"}
    )


# OAuth2 Authentication
@router.get("/oauth2-auth")
async def oauth2_auth_endpoint(current_user: User = Depends(get_current_user_oauth2)):
    """Endpoint protected by OAuth2 authentication"""
    return JSONResponse(
        {"message": "Access granted via OAuth2", "user": current_user.username, "auth_method": "oauth2"}
    )


# Scope-based authorization
@router.get("/admin")
async def admin_endpoint(current_user: User = Depends(require_scope("admin"))):
    """Endpoint requiring admin scope"""
    return JSONResponse(
        {
            "message": "Admin access granted",
            "user": current_user.username,
            "scopes": current_user.scopes,
            "auth_method": "jwt_with_scope",
        }
    )


@router.get("/read-only")
async def read_only_endpoint(current_user: User = Depends(require_scope("read"))):
    """Endpoint requiring read scope"""
    return JSONResponse(
        {
            "message": "Read access granted",
            "user": current_user.username,
            "scopes": current_user.scopes,
            "auth_method": "jwt_with_scope",
        }
    )


# User management endpoints
@router.get("/users/me")
async def get_current_user_info(current_user: User = Depends(get_current_user_jwt)):
    """Get current user information"""
    return JSONResponse({"user": current_user.dict(), "message": "Current user information"})


@router.put("/users/me")
async def update_current_user(email: Optional[str] = Query(None), current_user: User = Depends(get_current_user_jwt)):
    """Update current user information"""
    user_data = users_db[current_user.username]

    if email:
        user_data["user_info"]["email"] = email

    updated_user = User(**user_data["user_info"])

    return JSONResponse({"message": "User updated successfully", "user": updated_user.dict()})


# Multiple authentication methods example
@router.get("/flexible-auth")
async def flexible_auth_endpoint(
    jwt_user: Optional[User] = Depends(lambda: None), api_key_user: Optional[User] = Depends(lambda: None)
):
    """Endpoint that accepts multiple authentication methods"""

    # Try JWT first
    try:
        jwt_user = await get_current_user_jwt()
        return JSONResponse({"message": "Access granted via JWT", "user": jwt_user.username, "auth_method": "jwt"})
    except AuthenticationError:
        pass

    # Try API Key
    try:
        api_key_user = await get_current_user_api_key()
        return JSONResponse(
            {"message": "Access granted via API Key", "user": api_key_user.username, "auth_method": "api_key"}
        )
    except AuthenticationError:
        pass

    raise AuthenticationError("Authentication required (JWT or API Key)")


# Security info endpoint
@router.get("/security-info")
async def get_security_info():
    """Get information about available security schemes"""
    return JSONResponse(
        {
            "available_schemes": {
                "http_basic": {
                    "description": "HTTP Basic Authentication",
                    "header": "Authorization: Basic <base64(username:password)>",
                },
                "bearer_token": {
                    "description": "Bearer Token Authentication",
                    "header": "Authorization: Bearer <token>",
                },
                "jwt_token": {
                    "description": "JWT Token Authentication",
                    "header": "Authorization: Bearer <jwt_token>",
                    "endpoint": "/token",
                },
                "api_key": {"description": "API Key Authentication", "header": "X-API-Key: <api_key>"},
                "oauth2": {"description": "OAuth2 Password Flow", "token_url": "/token"},
            },
            "test_users": list(users_db.keys()),
            "endpoints": {
                "public": "/api/v1/public",
                "register": "/register",
                "login": "/token",
                "protected": [
                    "/api/v1/basic-auth",
                    "/api/v1/bearer-auth",
                    "/api/v1/jwt-auth",
                    "/api/v1/api-key-auth",
                    "/api/v1/oauth2-auth",
                ],
                "scoped": ["/api/v1/admin (requires 'admin' scope)", "/api/v1/read-only (requires 'read' scope)"],
            },
        }
    )


# Include router
app.include_router(router)


# Add sample data on startup
@app.on_startup
async def create_sample_data():
    """Create sample users and API keys for testing"""

    # Create admin user
    admin_password_hash, admin_salt = hash_password("admin123")
    admin_user = User(username="admin", email="admin@example.com", scopes=["read", "write", "admin"])

    users_db["admin"] = {"user_info": admin_user.dict(), "password_hash": admin_password_hash, "salt": admin_salt}

    # Create regular user
    user_password_hash, user_salt = hash_password("user123")
    regular_user = User(username="user", email="user@example.com", scopes=["read", "write"])

    users_db["user"] = {"user_info": regular_user.dict(), "password_hash": user_password_hash, "salt": user_salt}

    # Create API keys
    admin_api_key = "admin_" + generate_secret_key()
    user_api_key = "user_" + generate_secret_key()

    api_keys_db[admin_api_key] = admin_user.id
    api_keys_db[user_api_key] = regular_user.id

    print("🔐 Security demo started!")
    print("\n👥 Test Users:")
    print("  - admin:admin123 (scopes: read, write, admin)")
    print("  - user:user123 (scopes: read, write)")
    print(f"\n🔑 API Keys:")
    print(f"  - Admin: {admin_api_key}")
    print(f"  - User: {user_api_key}")
    print(f"\n🔒 Secret Key: {SECRET_KEY}")
    print("\n🌐 Available endpoints:")
    print("  - GET /api/v1/security-info (security information)")
    print("  - POST /register (user registration)")
    print("  - POST /token (OAuth2 token endpoint)")
    print("  - GET /api/v1/public (no auth required)")
    print("  - GET /api/v1/*-auth (various auth methods)")


if __name__ == "__main__":
    import uvicorn

    print("Starting Security Demo...")
    print("Visit http://localhost:8000/docs for interactive documentation")

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
