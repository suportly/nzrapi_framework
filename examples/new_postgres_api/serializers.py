from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from examples.new_postgres_api.models import Category, Item, Order, OrderItem, OrderStatus, Product, User, UserRole
from nzrapi.security import hash_password
from nzrapi.serializers import CharField, ModelSerializer, ValidationError


# User Serializers
class UserCreateSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "password", "full_name", "role"]
        extra_kwargs = {"password": {"write_only": True}, "role": {"required": False}}

    async def create(self, validated_data: Dict[str, Any], session: AsyncSession) -> User:
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        session.add(user)
        await session.flush()
        await session.refresh(user)
        return user


class UserUpdateSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "full_name", "is_active", "role"]
        extra_kwargs = {"email": {"required": False}, "is_active": {"required": False}, "role": {"required": False}}


class UserResponseSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "full_name", "role", "is_active", "created_at"]
        read_only_fields = fields


# Auth Serializers
class LoginSerializer(ModelSerializer):
    # Explicitly declare fields to ensure validation independent of model columns
    username = CharField()
    password = CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "password"]


class TokenResponseSerializer(ModelSerializer):
    access_token: str
    token_type: str = "bearer"

    class Meta:
        fields = ["access_token", "token_type"]


# Category Serializers
class CategorySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description"]
        read_only_fields = ["id"]


# Product Serializers
class ProductCreateUpdateSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = ["name", "description", "price", "stock_quantity", "is_available", "category_id"]


class ProductResponseSerializer(ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "stock_quantity",
            "is_available",
            "category_id",
            "category",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


# Order Serializers
class OrderItemSerializer(ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "product_id", "quantity", "unit_price"]
        read_only_fields = ["id", "unit_price"]


class OrderCreateUpdateSerializer(ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = ["shipping_address", "payment_details", "items"]

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data.get("items"):
            raise ValidationError("Order must contain at least one item")
        return data


class OrderResponseSerializer(ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status = CharField(read_only=True)  # Fixed EnumField reference

    class Meta:
        model = Order
        fields = [
            "id",
            "user_id",
            "status",
            "total_amount",
            "shipping_address",
            "payment_details",
            "created_at",
            "updated_at",
            "items",
        ]
        read_only_fields = fields


# Item Serializers (kept for backward compatibility)
class ItemSerializer(ModelSerializer):
    class Meta:
        model = Item
        fields = ["id", "name", "description", "price", "is_available", "extra_data", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
