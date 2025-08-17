"""
Basic nzrRest API Example

This example demonstrates the fundamental features of nzrRest framework:
- Creating an application
- Adding routes
- Using serializers
- Basic AI model integration
"""

import asyncio

from nzrrest import JSONResponse, NzrRestApp, Request, Router
from nzrrest.ai.models import MockAIModel
from nzrrest.middleware import RateLimitMiddleware, RequestLoggingMiddleware
from nzrrest.serializers import BaseSerializer, CharField, IntegerField

# Create the application
app = NzrRestApp(title="Basic nzrRest API", version="1.0.0", debug=True)

# Add middleware
app.add_middleware(RequestLoggingMiddleware, log_level="INFO")
app.add_middleware(RateLimitMiddleware, calls_per_minute=30)

# Create a router
router = Router()


# Serializers
class UserSerializer(BaseSerializer):
    """Example user serializer"""

    name = CharField(max_length=100)
    age = IntegerField(min_value=0, max_value=150)
    email = CharField()


class MessageSerializer(BaseSerializer):
    """Message serializer for AI chat"""

    message = CharField(max_length=1000)
    user_id = CharField(required=False)


# Routes
@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to nzrRest Basic API",
        "framework": "nzrRest",
        "version": "1.0.0",
    }


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "framework": "nzrRest"}


@router.post("/users")
async def create_user(request: Request):
    """Create a new user with validation"""
    try:
        data = await request.json()

        # Validate input using serializer
        serializer = UserSerializer(data=data)
        if not serializer.is_valid():
            return JSONResponse(
                {"error": "Validation failed", "details": serializer.errors},
                status_code=422,
            )

        # In a real app, you'd save to database here
        user_data = serializer.validated_data
        user_data["id"] = 1  # Mock ID

        return {"message": "User created successfully", "user": user_data}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get user by ID"""
    # Mock user data
    if user_id == 1:
        return {"id": 1, "name": "John Doe", "age": 30, "email": "john@example.com"}
    else:
        return JSONResponse({"error": "User not found"}, status_code=404)


@router.post("/chat")
async def chat_with_ai(request: Request):
    """Chat with AI model"""
    try:
        data = await request.json()

        # Validate input
        serializer = MessageSerializer(data=data)
        if not serializer.is_valid():
            return JSONResponse(
                {"error": "Validation failed", "details": serializer.errors},
                status_code=422,
            )

        # Get AI model from registry
        ai_model = request.app.ai_registry.get_model("basic_chat")
        if not ai_model:
            return JSONResponse({"error": "AI model not available"}, status_code=503)

        # Make prediction
        validated_data = serializer.validated_data
        result = await ai_model.predict(
            {
                "prompt": validated_data["message"],
                "user_id": validated_data.get("user_id"),
            }
        )

        return {
            "response": result.get("response", "No response generated"),
            "model": ai_model.name,
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/models")
async def list_models(request: Request):
    """List available AI models"""
    models = request.app.ai_registry.list_models()
    return {"models": models}


# Include router in app
app.include_router(router)


# Startup event to initialize AI models
@app.on_startup
async def startup():
    """Initialize the application"""
    print("🚀 Starting Basic nzrRest API...")

    # Add a basic chat model
    await app.ai_registry.add_model(
        name="basic_chat",
        model_type="mock",
        config={
            "name": "basic_chat",
            "version": "1.0.0",
            "provider": "mock",
            "mock_responses": {
                "hello": "Hello! I'm a basic AI assistant built with nzrRest.",
                "how are you": "I'm functioning well! How can I help you today?",
                "bye": "Goodbye! Have a great day!",
            },
            "simulation_delay": 0.1,
        },
    )

    # Load the model
    await app.ai_registry.get_model("basic_chat").load_model()

    print("✅ Basic chat model loaded")
    print("📝 API Documentation available at: http://localhost:8000/docs")


@app.on_shutdown
async def shutdown():
    """Cleanup on shutdown"""
    print("🛑 Shutting down Basic nzrRest API...")


if __name__ == "__main__":
    import uvicorn

    print("Starting nzrRest Basic API Example...")
    print("Visit http://localhost:8000 to try the API")
    print("Example requests:")
    print("  GET  /health")
    print("  POST /users")
    print("  POST /chat")
    print("  GET  /models")

    uvicorn.run("basic_api:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
