from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from nzrapi.db.fields import (
    BooleanColumn,
    DateTimeColumn,
    EnumColumn,
    FloatColumn,
    IntegerColumn,
    JSONColumn,
    StringColumn,
    TextColumn,
)
from nzrapi.db.models import Model
from nzrapi.security import hash_password
from nzrapi.security import verify_password as verify_pwd


class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    CUSTOMER = "customer"


class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Category(Model):
    __tablename__ = "categories"

    id = IntegerColumn(primary_key=True, index=True)
    name = StringColumn(unique=True, index=True, max_length=50)
    description = TextColumn(nullable=True)

    # Relationships
    products = relationship("Product", back_populates="category")


class User(Model):
    __tablename__ = "users"

    id = IntegerColumn(primary_key=True, index=True)
    username = StringColumn(unique=True, index=True, max_length=50)
    email = StringColumn(unique=True, index=True, max_length=100)
    hashed_password = StringColumn(max_length=255)
    password_salt = StringColumn(max_length=32)
    full_name = StringColumn(max_length=100, nullable=True)
    is_active = BooleanColumn(default=True)
    role = EnumColumn(UserRole, default=UserRole.CUSTOMER)
    created_at = DateTimeColumn(default=datetime.utcnow)
    updated_at = DateTimeColumn(default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.hashed_password, self.password_salt = hash_password(password)

    def verify_password(self, password: str) -> bool:
        return verify_pwd(password, self.hashed_password, self.password_salt)


class Product(Model):
    __tablename__ = "products"

    id = IntegerColumn(primary_key=True, index=True)
    name = StringColumn(index=True, max_length=100)
    description = TextColumn(nullable=True)
    price = FloatColumn()
    stock_quantity = IntegerColumn(default=0)
    is_available = BooleanColumn(default=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    created_at = DateTimeColumn(default=datetime.utcnow)
    updated_at = DateTimeColumn(default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")


class Order(Model):
    __tablename__ = "orders"

    id = IntegerColumn(primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    status = EnumColumn(OrderStatus, default=OrderStatus.PENDING)
    total_amount = FloatColumn(default=0.0)
    shipping_address = TextColumn()
    payment_details = JSONColumn(nullable=True)
    created_at = DateTimeColumn(default=datetime.utcnow)
    updated_at = DateTimeColumn(default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Model):
    __tablename__ = "order_items"

    id = IntegerColumn(primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    quantity = IntegerColumn(default=1)
    unit_price = FloatColumn()

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Item(Model):
    __tablename__ = "items"

    id = IntegerColumn(primary_key=True, index=True)
    name = StringColumn(index=True, max_length=100)
    description = TextColumn(nullable=True)
    price = FloatColumn()
    is_available = BooleanColumn(default=True)
    extra_data = JSONColumn(nullable=True)  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    created_at = DateTimeColumn(default=datetime.utcnow)
    updated_at = DateTimeColumn(default=datetime.utcnow, onupdate=datetime.utcnow)
