"""
NzrApi PostgreSQL API Example

This example demonstrates how to use NzrApi with a PostgreSQL database for CRUD operations.

Prerequisites:
- A running PostgreSQL server.
- A database and user matching the DATABASE_URL.
- `asyncpg` driver installed (`pip install asyncpg`).

To run this example:
1. Make sure your PostgreSQL server is running and accessible.
2. Run the script: `python examples/postgres_api.py`
"""

import uvicorn
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

from nzrapi import JSONResponse, NzrApiApp, Request, get_session_reliable, with_db_session
from nzrapi.serializers import BaseSerializer, CharField, IntegerField

# --- Database Configuration ---
DATABASE_URL = "postgresql+asyncpg://n8n:xjoA531Gs24zKUwXRMdc@localhost:5432/fanboost"

Base = declarative_base()


# --- SQLAlchemy Model ---
class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)


# --- Serializers for Data Validation ---
class ItemSerializer(BaseSerializer):
    name = CharField(max_length=100)
    description = CharField(required=False)


# --- Application Setup ---
app = NzrApiApp(
    title="NzrApi PostgreSQL API",
    version="1.0.0",
    debug=True,
    debug_level="verbose",  # 🆕 Debug melhorado para DB operations
    database_url=DATABASE_URL,
)


# --- API Endpoints ---
@app.post("/items")
@with_db_session  # 🆕 Session automaticamente injetada!
async def create_item(session: AsyncSession, request: Request):
    """Create a new item in the database."""
    data = await request.json()
    serializer = ItemSerializer(data=data)
    if not serializer.is_valid():
        return JSONResponse(
            {"error": "Validation failed", "details": serializer.errors},
            status_code=422,
        )

    new_item = Item(**serializer.validated_data)
    # 🆕 Session já disponível, sem context manager!
    session.add(new_item)
    await session.commit()
    await session.refresh(new_item)
    return {
        "id": new_item.id,
        "name": new_item.name,
        "description": new_item.description,
    }


@app.get("/items")
@with_db_session  # 🆕 Session automaticamente injetada!
async def get_all_items(session: AsyncSession, request: Request):
    """Retrieve all items from the database."""
    # 🆕 Session já disponível diretamente!
    result = await session.execute(select(Item))
    items = result.scalars().all()
    return [{"id": item.id, "name": item.name, "description": item.description} for item in items]


@app.get("/items/{item_id}")
@with_db_session  # 🆕 Session automaticamente injetada!
async def get_item(session: AsyncSession, request: Request, item_id: int):
    """Retrieve a single item by its ID."""
    # 🆕 Session já disponível diretamente!
    item = await session.get(Item, item_id)
    if not item:
        return JSONResponse({"error": "Item not found"}, status_code=404)
    return {"id": item.id, "name": item.name, "description": item.description}


@app.put("/items/{item_id}")
@with_db_session  # 🆕 Session automaticamente injetada!
async def update_item(session: AsyncSession, request: Request, item_id: int):
    """Update an existing item."""
    data = await request.json()
    serializer = ItemSerializer(data=data)
    if not serializer.is_valid():
        return JSONResponse(
            {"error": "Validation failed", "details": serializer.errors},
            status_code=422,
        )

    # 🆕 Session já disponível diretamente!
    item = await session.get(Item, item_id)
    if not item:
        return JSONResponse({"error": "Item not found"}, status_code=404)

    for key, value in serializer.validated_data.items():
        setattr(item, key, value)

    await session.commit()
    await session.refresh(item)
    return {"id": item.id, "name": item.name, "description": item.description}


@app.delete("/items/{item_id}")
@with_db_session  # 🆕 Session automaticamente injetada!
async def delete_item(session: AsyncSession, request: Request, item_id: int):
    """Delete an item from the database."""
    # 🆕 Session já disponível diretamente!
    item = await session.get(Item, item_id)
    if not item:
        return JSONResponse({"error": "Item not found"}, status_code=404)

    await session.delete(item)
    await session.commit()
    return {"message": f"Item {item_id} deleted successfully"}


# --- Startup Event ---
@app.on_startup
async def startup():
    """Create database tables on application startup."""
    print("🚀 Starting PostgreSQL API...")
    async with app.db_manager.engine.begin() as conn:
        # Drop all tables (for demonstration purposes, remove in production)
        # await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created.")


# --- Runnable Main Block ---
if __name__ == "__main__":
    print("Starting NzrApi PostgreSQL API Example...")
    print("Visit http://localhost:8003 to try the API")
    uvicorn.run("postgres_api:app", host="0.0.0.0", port=8003, reload=True, log_level="info")
