"""
API endpoints for {{ project_name }}
"""
from nzrapi import JSONResponse, Request, Router
from nzrapi.serializers import BaseSerializer, CharField, IntegerField

router = Router()


# Serializers
class ItemSerializer(BaseSerializer):
    """Serializer for item data"""

    id = IntegerField()
    name = CharField()
    description = CharField(required=False)


@router.get("/")
async def read_root():
    """Welcome endpoint"""
    return {"message": "Welcome to the {{ project_name }} API!"}


@router.get("/items/{item_id}")
async def read_item(request: Request, item_id: int):
    """
    Example endpoint to retrieve an item.
    """
    # In a real application, you would fetch this data from a database
    # or another service.
    item_data = {
        "id": item_id,
        "name": f"Sample Item {item_id}",
        "description": "This is a sample item description.",
    }

    # Validate and serialize the output data
    serializer = ItemSerializer(data=item_data)
    if not serializer.is_valid():
        return JSONResponse(
            {"error": "Internal data validation failed", "details": serializer.errors},
            status_code=500,
        )

    return JSONResponse(serializer.validated_data)


@router.post("/items")
async def create_item(request: Request):
    """
    Example endpoint to create an item.
    """
    body = await request.json()

    # In a real application, you would validate the input
    # and save it to a database.

    # For this example, we'll just echo back the received data
    # after adding an ID.
    new_item = body.copy()
    new_item["id"] = 123  # dummy id

    serializer = ItemSerializer(data=new_item)
    if not serializer.is_valid():
        return JSONResponse(
            {"error": "Invalid request payload", "details": serializer.errors},
            status_code=422,
        )

    return JSONResponse(serializer.validated_data, status_code=201)
