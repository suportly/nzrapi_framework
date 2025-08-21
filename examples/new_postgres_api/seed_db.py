#!/usr/bin/env python3
"""
Database seeder script for the NzrApi example application.

This script populates the database with sample data for testing and development.
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from faker import Faker
from sqlalchemy import select

from examples.new_postgres_api.main import app
from examples.new_postgres_api.models import Category, Order, OrderItem, OrderStatus, Product, User, UserRole

# Initialize Faker
fake = Faker()

# Sample data
PRODUCT_CATEGORIES = [
    "Electronics",
    "Clothing",
    "Books",
    "Home & Kitchen",
    "Sports & Outdoors",
    "Beauty & Personal Care",
    "Toys & Games",
    "Health & Household",
]

PRODUCT_NAMES = {
    "Electronics": ["Smartphone", "Laptop", "Headphones", "Smart Watch", "Tablet"],
    "Clothing": ["T-Shirt", "Jeans", "Dress", "Jacket", "Sneakers"],
    "Books": ["Novel", "Textbook", "Cookbook", "Biography", "Self-Help"],
    "Home & Kitchen": ["Blender", "Knife Set", "Cookware Set", "Air Fryer", "Coffee Maker"],
    "Sports & Outdoors": ["Yoga Mat", "Running Shoes", "Tent", "Bicycle", "Dumbbell Set"],
    "Beauty & Personal Care": ["Shampoo", "Moisturizer", "Perfume", "Makeup Kit", "Hair Dryer"],
    "Toys & Games": ["Board Game", "LEGO Set", "Doll", "Action Figure", "Puzzle"],
    "Health & Household": ["Vitamins", "First Aid Kit", "Air Purifier", "Humidifier", "Scale"],
}


async def create_admin_user(session) -> User:
    """Create an admin user if one doesn't exist."""
    admin = await session.execute(select(User).where(User.username == "admin"))
    admin = admin.scalar_one_or_none()

    if not admin:
        admin = User(
            username="admin",
            email="admin@example.com",
            full_name="Admin User",
            role=UserRole.ADMIN,
            is_active=True,
        )
        admin.set_password("secret")  # Set password using the proper method
        session.add(admin)
        await session.commit()
        print("Created admin user")

    return admin


async def create_categories(session) -> Dict[str, Category]:
    """Create product categories."""
    categories = {}
    for name in PRODUCT_CATEGORIES:
        # Check if category exists
        stmt = select(Category).where(Category.name == name)
        result = await session.execute(stmt)
        category = result.scalar_one_or_none()

        if not category:
            category = Category(name=name, description=f"{name} products and accessories")
            session.add(category)
            await session.commit()
            print(f"Created category: {name}")

        categories[name] = category

    return categories


async def create_products(session, categories: Dict[str, Category], count: int = 50) -> List[Product]:
    """Create sample products."""
    products = []

    # First create products from our predefined list
    for category_name, product_names in PRODUCT_NAMES.items():
        category = categories[category_name]

        for product_name in product_names:
            product = Product(
                name=product_name,
                description=f"High-quality {product_name.lower()} for all your needs.",
                price=round(random.uniform(10, 1000), 2),
                stock_quantity=random.randint(0, 100),
                is_available=random.choice([True, True, True, False]),  # 75% chance of being available
                category_id=category.id,
            )
            session.add(product)
            products.append(product)

    # Then create some random products
    for _ in range(count - len(products)):
        category = random.choice(list(categories.values()))
        product_name = fake.unique.word().capitalize()

        product = Product(
            name=product_name,
            description=fake.sentence(),
            price=round(random.uniform(1, 1000), 2),
            stock_quantity=random.randint(0, 200),
            is_available=random.choice([True, True, True, False]),
            category_id=category.id,
        )
        session.add(product)
        products.append(product)

    await session.commit()
    print(f"Created {len(products)} products")
    return products


async def create_customers(session, count: int = 10) -> List[User]:
    """Create sample customer users."""
    customers = []

    for _ in range(count):
        first_name = fake.first_name()
        last_name = fake.last_name()
        username = f"{first_name.lower()}.{last_name.lower()}"
        email = f"{username}@example.com"

        # Check if user exists
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                username=username,
                email=email,
                full_name=f"{first_name} {last_name}",
                role=UserRole.CUSTOMER,
                is_active=True,
            )
            user.set_password("secret")  # Set password using the proper method
            session.add(user)
            customers.append(user)

    await session.commit()
    print(f"Created {len(customers)} customers")
    return customers


async def create_orders(session, customers: List[User], products: List[Product], count: int = 100) -> List[Order]:
    """Create sample orders."""
    statuses = list(OrderStatus)
    orders = []

    for _ in range(count):
        customer = random.choice(customers)
        order_date = fake.date_time_between(start_date="-1y", end_date="now")
        status = random.choices(
            statuses, weights=[0.4, 0.2, 0.2, 0.15, 0.05], k=1  # 40% PENDING, 20% PROCESSING, etc.
        )[0]

        order = Order(
            user_id=customer.id,
            status=status,
            shipping_address=fake.address(),
            created_at=order_date,
            updated_at=order_date,
        )
        session.add(order)

        # Add 1-5 random products to the order
        order_items = random.sample(products, k=random.randint(1, 5))
        total_amount = 0

        for product in order_items:
            quantity = random.randint(1, 5)
            unit_price = product.price * (1 - random.uniform(0, 0.3))  # Up to 30% discount
            total_amount += quantity * unit_price

            order_item = OrderItem(order=order, product=product, quantity=quantity, unit_price=unit_price)
            session.add(order_item)

        order.total_amount = total_amount
        orders.append(order)

    await session.commit()
    print(f"Created {len(orders)} orders")
    return orders


async def main():
    """Main function to seed the database."""
    print("Starting database seeding...")

    # Connect to database
    await app.db_manager.connect()

    try:
        async with app.db_manager.get_session() as session:
            # Create admin user
            admin = await create_admin_user(session)

            # Create categories
            categories = await create_categories(session)

            # Create products
            products = await create_products(session, categories)

            # Create customers (including the admin)
            customers = await create_customers(session)
            if admin not in customers:
                customers.append(admin)

            # Create orders
            await create_orders(session, customers, products)

        print("Database seeding completed successfully!")
    finally:
        await app.db_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
