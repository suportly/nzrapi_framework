"""
NzrApi Quick Start Example - Authentication and CRUD
This example shows the SIMPLEST way to get started with nzrapi.
"""

from sqlalchemy import Column, Integer, String, select

from nzrapi import (
    CORSMiddleware,
    JSONResponse,
    Middleware,
    NzrApiApp,
    Request,
    Router,
    check_password_hash,
    create_password_hash,
    with_db_session,
)
from nzrapi.db.models import Model


# 1. DEFINE YOUR MODEL (Standard SQLAlchemy)
class User(Model):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    password_hash = Column(String)
    name = Column(String)


# 2. CREATE ROUTER
router = Router()


# 3. SIMPLE AUTH ENDPOINTS (Function-based, easy to understand)
@router.post("/register")
@with_db_session  # This decorator handles database session automatically
async def register(session, request: Request):
    """Register new user - SIMPLE pattern."""
    data = await request.json()

    # Simple password hashing
    password_hash = create_password_hash(data["password"])

    user = User(email=data["email"], password_hash=password_hash, name=data["name"])

    session.add(user)
    await session.commit()

    return JSONResponse({"message": "User created successfully", "user_id": user.id})


@router.post("/login")
@with_db_session
async def login(session, request: Request):
    """Login user - SIMPLE pattern."""
    data = await request.json()

    # Simple database query
    result = await session.execute(select(User).where(User.email == data["email"]))
    user = result.scalar_one_or_none()

    if not user or not check_password_hash(data["password"], user.password_hash):
        return JSONResponse({"error": "Invalid credentials"}, status_code=401)

    return JSONResponse(
        {"message": "Login successful", "user": {"id": user.id, "name": user.name, "email": user.email}}
    )


# 4. SIMPLE CRUD ENDPOINT
@router.get("/users")
@with_db_session
async def list_users(session, request: Request):
    """List users - SIMPLE pattern."""
    result = await session.execute(select(User))
    users = result.scalars().all()

    return JSONResponse({"users": [{"id": u.id, "name": u.name, "email": u.email} for u in users]})


# 5. CREATE APP (Minimal configuration)
app = NzrApiApp(
    title="My Simple API",
    database_url="postgresql+asyncpg://user:pass@localhost/dbname",
    debug=True,
    debug_level="verbose",  # NEW: Helpful debugging
    middleware=[Middleware(CORSMiddleware, allow_origins=["*"])],
)

# 6. INCLUDE ROUTER
app.include_router(router, prefix="/api")

# 7. RUN IT
# uvicorn quick_start:app --reload --port 8000
# Then visit: http://localhost:8000/docs

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
