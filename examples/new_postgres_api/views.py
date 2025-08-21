from datetime import timedelta
from typing import Any, Dict, List, Optional, Type

from sqlalchemy import select

from examples.new_postgres_api.models import (
    Category,
    Item,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    User,
    UserRole,
)
from examples.new_postgres_api.serializers import (
    CategorySerializer,
    ItemSerializer,
    LoginSerializer,
    OrderCreateUpdateSerializer,
    OrderItemSerializer,
    OrderResponseSerializer,
    ProductCreateUpdateSerializer,
    ProductResponseSerializer,
    TokenResponseSerializer,
    UserCreateSerializer,
    UserResponseSerializer,
    UserUpdateSerializer,
)
from nzrapi import JSONResponse
from nzrapi.decorators import transactional
from nzrapi.permissions import (
    SAFE_METHODS,
    AllowAny,
    BasePermission,
    IsAdminUser,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from nzrapi.security import JWTBearer, create_access_token
from nzrapi.views import (
    APIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    status,
)


# Custom Permissions
class IsOwnerOrAdmin(BasePermission):
    """
    Permission that only allows the owner of an object or an admin to access it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in SAFE_METHODS:
            return True

        # Instance must have an attribute named 'user'.
        return obj.user_id == request.user.id or request.user.role == UserRole.ADMIN


# Auth Views
class RegisterView(APIView):
    permission_classes = [AllowAny]
    serializer_class = UserCreateSerializer
    response_serializer = UserResponseSerializer

    @transactional
    async def post(self, request, session=None):
        data = await request.json()
        serializer = self.serializer_class(data=data)
        if not serializer.is_valid():
            return JSONResponse(serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

        user = await serializer.save(session=session)
        response_serializer = self.response_serializer(user)
        return JSONResponse(response_serializer.data, status_code=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer
    response_serializer = TokenResponseSerializer

    async def post(self, request):
        # Accept JSON or form-encoded data
        try:
            data = await request.json()
        except Exception:
            form = await request.form()
            data = dict(form)
        serializer = self.serializer_class(data=data)
        if not serializer.is_valid():
            return JSONResponse(serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

        session = request.state.db_session
        result = await session.execute(select(User).where(User.username == serializer.validated_data["username"]))
        user = result.scalar_one_or_none()

        if not user or not user.verify_password(serializer.validated_data["password"]):
            return JSONResponse({"detail": "Incorrect username or password"}, status_code=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return JSONResponse({"detail": "User account is disabled"}, status_code=status.HTTP_403_FORBIDDEN)

        # Create JWT token
        access_token = create_access_token(
            data={"sub": str(user.id), "role": user.role},
            secret_key=request.app.state.secret_key,
            expires_delta=timedelta(days=1),
        )

        response_data = {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponseSerializer(user).data,
        }
        return JSONResponse(response_data)


# User Views
class UserListView(ListCreateAPIView):
    model_class = User
    serializer_class = UserResponseSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ["username", "email", "role", "is_active"]
    ordering_fields = ["id", "username", "email", "created_at"]
    search_fields = ["username", "email", "full_name"]


class UserDetailView(RetrieveUpdateDestroyAPIView):
    model_class = User
    serializer_class = UserUpdateSerializer
    response_serializer = UserResponseSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    lookup_field = "id"
    lookup_url_kwarg = "user_id"

    def get_serializer_class(self):
        if self.request.method == "GET":
            return self.response_serializer
        return self.serializer_class


# Category Views
class CategoryListView(ListCreateAPIView):
    model_class = Category
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ["name"]
    search_fields = ["name", "description"]


class CategoryDetailView(RetrieveUpdateDestroyAPIView):
    model_class = Category
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = "id"
    lookup_url_kwarg = "category_id"


# Product Views
class ProductListView(ListCreateAPIView):
    model_class = Product
    serializer_class = ProductCreateUpdateSerializer
    response_serializer = ProductResponseSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ["category_id", "is_available", "price"]
    ordering_fields = ["id", "name", "price", "created_at"]
    search_fields = ["name", "description"]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return self.response_serializer
        return self.serializer_class


class ProductDetailView(RetrieveUpdateDestroyAPIView):
    model_class = Product
    serializer_class = ProductCreateUpdateSerializer
    response_serializer = ProductResponseSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = "id"
    lookup_url_kwarg = "product_id"

    def get_serializer_class(self):
        if self.request.method == "GET":
            return self.response_serializer
        return self.serializer_class


# Order Views
class OrderListView(ListCreateAPIView):
    model_class = Order
    serializer_class = OrderCreateUpdateSerializer
    response_serializer = OrderResponseSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "user_id"]
    ordering_fields = ["id", "created_at", "total_amount"]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return self.response_serializer
        return self.serializer_class


class OrderDetailView(RetrieveUpdateDestroyAPIView):
    model_class = Order
    serializer_class = OrderCreateUpdateSerializer
    response_serializer = OrderResponseSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    lookup_field = "id"
    lookup_url_kwarg = "order_id"

    def get_serializer_class(self):
        if self.request.method == "GET":
            return self.response_serializer
        return self.serializer_class


# Item Views (kept for backward compatibility)
class ItemListView(ListCreateAPIView):
    model_class = Item
    serializer_class = ItemSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["is_available", "price"]
    ordering_fields = ["id", "name", "price", "created_at"]
    search_fields = ["name", "description"]


class ItemDetailView(RetrieveUpdateDestroyAPIView):
    model_class = Item
    serializer_class = ItemSerializer
    permission_classes = [AllowAny]
    lookup_field = "id"
    lookup_url_kwarg = "item_id"
