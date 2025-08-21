from examples.new_postgres_api.views import (  # Auth; Users; Categories; Products; Orders; Items (kept for backward compatibility)
    CategoryDetailView,
    CategoryListView,
    ItemDetailView,
    ItemListView,
    LoginView,
    OrderDetailView,
    OrderListView,
    ProductDetailView,
    ProductListView,
    RegisterView,
    UserDetailView,
    UserListView,
)
from nzrapi.routing import Router
from nzrapi.security import JWTBearer

# JWT authentication instance
jwt_auth = JWTBearer(secret_key="your-secret-key-here")

router = Router()

# Authentication routes
router.add_route("/auth/register", RegisterView.as_view(), methods=["POST"])
router.add_route("/auth/login", LoginView.as_view(), methods=["POST"])

# User routes
router.add_route(
    "/users",
    UserListView.as_view(),
    methods=["GET", "POST"],
)
router.add_route(
    "/users/{user_id}",
    UserDetailView.as_view(),
    methods=["GET", "PATCH", "DELETE"],
)

# Category routes
router.add_route(
    "/categories",
    CategoryListView.as_view(),
    methods=["GET", "POST"],
)
router.add_route(
    "/categories/{category_id}",
    CategoryDetailView.as_view(),
    methods=["GET", "PATCH", "DELETE"],
)

# Product routes
router.add_route(
    "/products",
    ProductListView.as_view(),
    methods=["GET", "POST"],
)
router.add_route(
    "/products/{product_id}",
    ProductDetailView.as_view(),
    methods=["GET", "PATCH", "DELETE"],
)

# Order routes
router.add_route(
    "/orders",
    OrderListView.as_view(),
    methods=["GET", "POST"],
)
router.add_route(
    "/orders/{order_id}",
    OrderDetailView.as_view(),
    methods=["GET", "PATCH", "DELETE"],
)

# Item routes (kept for backward compatibility)
router.add_route(
    "/items",
    ItemListView.as_view(),
    methods=["GET", "POST"],
)
router.add_route(
    "/items/{item_id}",
    ItemDetailView.as_view(),
    methods=["GET", "PUT", "PATCH", "DELETE"],
)
