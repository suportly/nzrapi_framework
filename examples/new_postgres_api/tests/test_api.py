from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Dict

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from starlette import status

from examples.new_postgres_api.main import app
from examples.new_postgres_api.models import Category, Order, OrderItem, Product, User, UserRole
from examples.new_postgres_api.serializers import UserCreateSerializer
from nzrapi.db.models import Model
from nzrapi.security import create_access_token

# Test Database
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


# Test client
@pytest_asyncio.fixture(scope="module")
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    # Override the database URL for testing
    app.database_url = TEST_DATABASE_URL

    # Create test database and tables
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)

    # Create test client
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Model.metadata.drop_all)
    await engine.dispose()


# Test session
@pytest_asyncio.fixture(scope="function")
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DATABASE_URL)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        yield session
        await session.rollback()

    await engine.dispose()


# Test user data
@pytest.fixture
def test_user_data() -> Dict[str, Any]:
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User",
    }


# Test admin user
@pytest_asyncio.fixture
async def test_admin(test_session: AsyncSession) -> User:
    user_data = {
        "username": "admin",
        "email": "admin@example.com",
        "hashed_password": "hashedpassword",  # In a real test, you'd hash this
        "full_name": "Admin User",
        "role": UserRole.ADMIN,
        "is_active": True,
    }
    user = User(**user_data)
    test_session.add(user)
    await test_session.commit()
    return user


# Test token
@pytest.fixture
def test_token(test_admin: User) -> str:
    return create_access_token(
        data={"sub": str(test_admin.id), "role": test_admin.role},
        secret_key="testsecret",
        expires_delta=timedelta(minutes=30),
    )


# Test authenticated client
@pytest.fixture
def authenticated_client(test_client: AsyncClient, test_token: str) -> AsyncClient:
    test_client.headers.update({"Authorization": f"Bearer {test_token}"})
    return test_client


# Tests
class TestAuth:
    async def test_register_user(self, test_client: AsyncClient, test_user_data: Dict[str, Any]):
        response = await test_client.post("/api/auth/register", json=test_user_data)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
        assert "password" not in data  # Password should not be in response

    async def test_login_user(self, test_client: AsyncClient, test_user_data: Dict[str, Any]):
        # First register
        await test_client.post("/api/auth/register", json=test_user_data)

        # Then login
        login_data = {"username": test_user_data["username"], "password": test_user_data["password"]}
        response = await test_client.post("/api/auth/login", data=login_data)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data


class TestUsers:
    async def test_get_users_unauthorized(self, test_client: AsyncClient):
        response = await test_client.get("/api/users")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_users_authorized(self, authenticated_client: AsyncClient):
        response = await authenticated_client.get("/api/users")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)


class TestProducts:
    async def test_create_product_unauthorized(self, test_client: AsyncClient):
        product_data = {"name": "Test Product", "price": 9.99}
        response = await test_client.post("/api/products", json=product_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_create_product_authorized(self, authenticated_client: AsyncClient):
        product_data = {
            "name": "Test Product",
            "description": "A test product",
            "price": 9.99,
            "stock_quantity": 10,
            "is_available": True,
        }
        response = await authenticated_client.post("/api/products", json=product_data)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == product_data["name"]
        assert data["price"] == product_data["price"]
        assert "id" in data


class TestOrders:
    async def test_create_order(self, authenticated_client: AsyncClient, test_session: AsyncSession):
        # Create a test product first
        product = Product(
            name="Test Product", description="Test Description", price=19.99, stock_quantity=10, is_available=True
        )
        test_session.add(product)
        await test_session.commit()

        order_data = {
            "shipping_address": "123 Test St, Test City",
            "items": [{"product_id": product.id, "quantity": 2, "unit_price": 19.99}],
        }

        response = await authenticated_client.post("/api/orders", json=order_data)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["shipping_address"] == order_data["shipping_address"]
        assert len(data["items"]) == 1
        assert data["items"][0]["product_id"] == product.id
        assert data["total_amount"] == 39.98  # 2 * 19.99


class TestHealthCheck:
    async def test_health_check(self, test_client: AsyncClient):
        response = await test_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
