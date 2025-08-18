from typing import AsyncGenerator

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from examples.new_postgres_api.main import NzrApiApp


@pytest.fixture
def app() -> NzrApiApp:
    from examples.new_postgres_api.main import app as main_app

    return main_app


@pytest_asyncio.fixture
async def client(app: NzrApiApp) -> AsyncGenerator[AsyncClient, None]:
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.mark.asyncio
async def test_create_item(client: AsyncClient):
    # Scenario
    item_data = {"name": "Test Item", "description": "This is a test item."}

    # Execution
    response = await client.post("/api/items", json=item_data)

    # Asserts
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == item_data["name"]
    assert data["description"] == item_data["description"]
    assert "id" in data


@pytest.mark.asyncio
async def test_list_items(client: AsyncClient):
    # Scenario: Create an item to ensure the list is not empty
    await client.post("/api/items", json={"name": "Item 1", "description": "First item"})

    # Execution
    response = await client.get("/api/items")

    # Asserts
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "count" in data
    assert "results" in data
    results = data["results"]
    assert isinstance(results, list)
    assert len(results) > 0
    assert "name" in results[0]


@pytest.mark.asyncio
async def test_retrieve_item(client: AsyncClient):
    # Scenario
    item_data = {"name": "Retrieve Me", "description": "Item to be retrieved."}
    create_response = await client.post("/api/items", json=item_data)
    item_id = create_response.json()["id"]

    # Execution
    response = await client.get(f"/api/items/{item_id}")

    # Asserts
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == item_id
    assert data["name"] == item_data["name"]


@pytest.mark.asyncio
async def test_update_item(client: AsyncClient):
    # Scenario
    item_data = {"name": "Update Me", "description": "Item to be updated."}
    create_response = await client.post("/api/items", json=item_data)
    item_id = create_response.json()["id"]
    update_data = {"name": "Updated Name", "description": "Updated description."}

    # Execution
    response = await client.put(f"/api/items/{item_id}", json=update_data)

    # Asserts
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]


@pytest.mark.asyncio
async def test_delete_item(client: AsyncClient):
    # Scenario
    item_data = {"name": "Delete Me", "description": "Item to be deleted."}
    create_response = await client.post("/api/items", json=item_data)
    item_id = create_response.json()["id"]

    # Execution
    delete_response = await client.delete(f"/api/items/{item_id}")

    # Asserts
    assert delete_response.status_code == 204

    # Verify the item is gone
    get_response = await client.get(f"/api/items/{item_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_search_items(client: AsyncClient):
    # Scenario: Create specific items to test search
    await client.post(
        "/api/items",
        json={
            "name": "Searchable Unique Item",
            "description": "A very specific description for searching.",
        },
    )
    await client.post(
        "/api/items", json={"name": "Another Item", "description": "Some other description."}
    )

    # Execution: Search for the unique item by name (case-insensitive)
    response = await client.get("/api/items?search=unique")

    # Asserts for name search
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    assert len(data["results"]) >= 1
    assert data["results"][0]["name"] == "Searchable Unique Item"

    # Execution: Search for the unique item by description
    response_desc = await client.get("/api/items?search=specific description")

    # Asserts for description search
    assert response_desc.status_code == 200
    data_desc = response_desc.json()
    assert data_desc["count"] >= 1
    assert len(data_desc["results"]) >= 1
    assert (
        data_desc["results"][0]["description"]
        == "A very specific description for searching."
    )

    # Execution: Search for a term that doesn't exist
    response_none = await client.get("/api/items?search=NonExistentTerm")

    # Asserts for non-existent search
    assert response_none.status_code == 200
    data_none = response_none.json()
    assert data_none["count"] == 0
    assert len(data_none["results"]) == 0
