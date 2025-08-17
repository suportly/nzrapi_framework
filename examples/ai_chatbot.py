"""
AI Chatbot Example with nzrRest Framework

This example demonstrates:
- Advanced AI model integration
- Conversation context management
- Custom AI model implementation
- WebSocket support for real-time chat
- Database integration for chat history
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Optional

# Database models
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession

from nzrrest import JSONResponse, NzrRestApp, Request, Router
from nzrrest.ai.context import ContextConfig, ContextManager
from nzrrest.ai.models import AIModel
from nzrrest.ai.protocol import MCPRequest, MCPResponse
from nzrrest.db import Base, init_database
from nzrrest.middleware import CORSMiddleware, RequestLoggingMiddleware
from nzrrest.serializers import BaseSerializer, BooleanField, CharField


class ChatMessage(Base):
    """Database model for chat messages"""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True, nullable=False)
    user_id = Column(String(255), index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    model_name = Column(String(100))
    metadata = Column(Text)  # JSON


class ChatSession(Base):
    """Database model for chat sessions"""

    __tablename__ = "chat_sessions"

    id = Column(String(255), primary_key=True, index=True)
    user_id = Column(String(255), index=True)
    title = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    model_name = Column(String(100))
    system_prompt = Column(Text)


# Custom AI Model for advanced chatbot
class AdvancedChatModel(AIModel):
    """Advanced chat model with personality and context awareness"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.personality = config.get("personality", "helpful")
        self.max_context_turns = config.get("max_context_turns", 10)
        self.system_prompt = config.get(
            "system_prompt",
            "You are a helpful AI assistant built with nzrRest framework.",
        )
        self.conversation_memory = {}

    async def load_model(self) -> None:
        """Load the advanced chat model"""
        await asyncio.sleep(0.2)  # Simulate loading
        self.is_loaded = True
        print(f"✅ Loaded advanced chat model: {self.name}")

    async def predict(self, payload: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
        """Advanced chat prediction with context and personality"""
        if not self.is_loaded:
            raise RuntimeError("Model not loaded")

        message = payload.get("message", "")
        session_id = payload.get("session_id", "default")
        user_id = payload.get("user_id")

        # Initialize conversation if new
        if session_id not in self.conversation_memory:
            self.conversation_memory[session_id] = {
                "messages": [{"role": "system", "content": self.system_prompt}],
                "user_id": user_id,
                "created_at": datetime.utcnow(),
            }

        conversation = self.conversation_memory[session_id]

        # Add user message
        conversation["messages"].append(
            {
                "role": "user",
                "content": message,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Trim conversation if too long
        if len(conversation["messages"]) > self.max_context_turns * 2 + 1:  # +1 for system message
            # Keep system message and recent turns
            system_msg = conversation["messages"][0]
            recent_msgs = conversation["messages"][-(self.max_context_turns * 2) :]
            conversation["messages"] = [system_msg] + recent_msgs

        # Generate response based on personality and context
        response_text = await self._generate_contextual_response(message, conversation, payload)

        # Add assistant response
        conversation["messages"].append(
            {
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        return {
            "response": response_text,
            "session_id": session_id,
            "model": self.name,
            "personality": self.personality,
            "turn_count": len(conversation["messages"]) // 2,
            "context_used": len(conversation["messages"]) > 2,
        }

    async def _generate_contextual_response(self, message: str, conversation: dict, payload: dict) -> str:
        """Generate contextual response based on conversation history"""
        message_lower = message.lower()

        # Analyze conversation context
        recent_messages = conversation["messages"][-4:]  # Last 2 turns
        context_topics = self._extract_topics(recent_messages)

        # Personality-based responses
        if self.personality == "friendly":
            greeting_words = ["hi", "hello", "hey", "good morning", "good afternoon"]
            if any(word in message_lower for word in greeting_words):
                return f"Hey there! 😊 Great to chat with you! What's on your mind today?"

        elif self.personality == "professional":
            if any(word in message_lower for word in ["hello", "hi"]):
                return "Good day! I'm here to assist you with any questions or tasks you may have."

        elif self.personality == "quirky":
            if "hello" in message_lower:
                return "Well hello there, human! 🤖 Ready for some digital conversation magic?"

        # Context-aware responses
        if "weather" in message_lower:
            return "I don't have access to real-time weather data, but I can help you find weather services or discuss weather-related topics!"

        if "time" in message_lower:
            return f"I don't have real-time clock access, but when you sent this message, it was processed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC."

        if any(word in message_lower for word in ["thank", "thanks"]):
            return "You're very welcome! I'm glad I could help. Is there anything else you'd like to know?"

        if any(word in message_lower for word in ["bye", "goodbye", "see you"]):
            return "Goodbye! It was great chatting with you. Feel free to come back anytime! 👋"

        # Technical questions about nzrRest
        if "nzrrest" in message_lower or "framework" in message_lower:
            return """nzrRest is a powerful Python framework for building AI APIs! Here are some key features:
            
            🤖 Native AI model integration
            🔄 Model Context Protocol (MCP) support  
            🚀 Async/await performance
            📊 Built-in context management
            🛡️ Production-ready middleware
            🗄️ Database integration with SQLAlchemy
            
            What aspect would you like to learn more about?"""

        # Programming help
        if any(word in message_lower for word in ["code", "program", "python", "api"]):
            return "I'd be happy to help with programming questions! I can assist with Python, API design, nzrRest framework usage, and general software development topics. What specific area are you working on?"

        # Contextual continuation
        if context_topics:
            if "programming" in context_topics and ("help" in message_lower or "how" in message_lower):
                return "Based on our conversation about programming, I can provide more specific guidance. Could you share what you're trying to build or what challenge you're facing?"

        # Default intelligent response
        return f"That's an interesting point about '{message}'. I'm here to help with questions, have conversations, or assist with tasks related to AI, programming, or the nzrRest framework. What would you like to explore further?"

    def _extract_topics(self, messages: list) -> list:
        """Extract topics from recent messages"""
        topics = []
        text = " ".join([msg.get("content", "") for msg in messages])
        text_lower = text.lower()

        topic_keywords = {
            "programming": ["code", "python", "api", "framework", "development"],
            "ai": ["ai", "model", "machine learning", "artificial intelligence"],
            "help": ["help", "assist", "support", "question"],
            "weather": ["weather", "temperature", "rain", "sunny"],
        }

        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)

        return topics

    async def unload_model(self) -> None:
        """Unload the model"""
        self.conversation_memory.clear()
        self.is_loaded = False
        print(f"❌ Unloaded advanced chat model: {self.name}")

    @property
    def model_info(self) -> Dict[str, str]:
        """Get model information"""
        return {
            "name": self.name,
            "version": self.version,
            "provider": self.provider,
            "type": "advanced_chat",
            "description": f"Advanced conversational AI with {self.personality} personality",
            "capabilities": "context_aware_chat,personality,conversation_memory",
            "personality": self.personality,
            "max_context_turns": str(self.max_context_turns),
        }


# Create application
app = NzrRestApp(
    title="AI Chatbot with nzrRest",
    version="1.0.0",
    database_url="sqlite+aiosqlite:///./chatbot.db",
    debug=True,
)

# Add middleware
app.add_middleware(CORSMiddleware, allow_origins=["*"])
app.add_middleware(RequestLoggingMiddleware, log_level="INFO")

# Create router
router = Router()

# Context manager for conversations
context_manager = ContextManager(
    ContextConfig(default_ttl=3600, max_contexts=1000, cleanup_interval=300)  # 1 hour  # 5 minutes
)


# Serializers
class ChatRequestSerializer(BaseSerializer):
    """Serializer for chat requests"""

    message = CharField(max_length=2000)
    session_id = CharField(required=False)
    user_id = CharField(required=False)
    model_name = CharField(required=False, default="advanced_chat")
    save_history = BooleanField(default=True)


class SessionSerializer(BaseSerializer):
    """Serializer for creating chat sessions"""

    title = CharField(max_length=255, required=False)
    user_id = CharField(required=False)
    model_name = CharField(required=False, default="advanced_chat")
    system_prompt = CharField(required=False)


# Routes
@router.post("/chat")
async def chat(request: Request):
    """Main chat endpoint with advanced context management"""
    try:
        data = await request.json()
        serializer = ChatRequestSerializer(data=data)

        if not serializer.is_valid():
            return JSONResponse(
                {"error": "Invalid request", "details": serializer.errors},
                status_code=422,
            )

        validated_data = serializer.validated_data

        # Generate session ID if not provided
        session_id = validated_data.get("session_id") or f"session_{datetime.utcnow().timestamp()}"

        # Get AI model
        model_name = validated_data["model_name"]
        ai_model = request.app.ai_registry.get_model(model_name)
        if not ai_model:
            return JSONResponse({"error": f"Model '{model_name}' not available"}, status_code=503)

        # Prepare payload
        payload = {
            "message": validated_data["message"],
            "session_id": session_id,
            "user_id": validated_data.get("user_id"),
        }

        # Make prediction
        result = await ai_model.predict(payload)

        # Save to database if requested
        if validated_data["save_history"]:
            await _save_chat_message(request, session_id, "user", validated_data["message"], model_name)
            await _save_chat_message(request, session_id, "assistant", result["response"], model_name)

        return {
            "response": result["response"],
            "session_id": session_id,
            "model": model_name,
            "metadata": {
                "personality": result.get("personality"),
                "turn_count": result.get("turn_count"),
                "context_used": result.get("context_used"),
            },
        }

    except Exception as e:
        return JSONResponse({"error": "Chat error", "details": str(e)}, status_code=500)


@router.post("/sessions")
async def create_session(request: Request):
    """Create a new chat session"""
    try:
        data = await request.json()
        serializer = SessionSerializer(data=data)

        if not serializer.is_valid():
            return JSONResponse(
                {"error": "Invalid request", "details": serializer.errors},
                status_code=422,
            )

        validated_data = serializer.validated_data
        session_id = f"session_{datetime.utcnow().timestamp()}"

        # Save session to database
        async with request.app.get_db_session() as session:
            chat_session = ChatSession(
                id=session_id,
                user_id=validated_data.get("user_id"),
                title=validated_data.get(
                    "title",
                    f"Chat Session {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                ),
                model_name=validated_data["model_name"],
                system_prompt=validated_data.get("system_prompt"),
            )
            session.add(chat_session)
            await session.commit()

        return {
            "session_id": session_id,
            "title": chat_session.title,
            "model_name": chat_session.model_name,
            "created_at": chat_session.created_at.isoformat(),
        }

    except Exception as e:
        return JSONResponse({"error": "Failed to create session", "details": str(e)}, status_code=500)


@router.get("/sessions/{session_id}/history")
async def get_chat_history(request: Request, session_id: str):
    """Get chat history for a session"""
    try:
        async with request.app.get_db_session() as session:
            from sqlalchemy import select

            # Get messages
            stmt = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.timestamp)
            result = await session.execute(stmt)
            messages = result.scalars().all()

            history = []
            for msg in messages:
                history.append(
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "model_name": msg.model_name,
                    }
                )

            return {
                "session_id": session_id,
                "message_count": len(history),
                "history": history,
            }

    except Exception as e:
        return JSONResponse({"error": "Failed to get history", "details": str(e)}, status_code=500)


@router.get("/models/{model_name}/personality")
async def get_model_personality(request: Request, model_name: str):
    """Get model personality and configuration"""
    try:
        model = request.app.ai_registry.get_model(model_name)
        if not model:
            return JSONResponse({"error": f"Model '{model_name}' not found"}, status_code=404)

        info = model.model_info
        stats = model.get_stats()

        return {
            "model_name": model_name,
            "personality": info.get("personality", "unknown"),
            "capabilities": info.get("capabilities", "").split(","),
            "max_context_turns": info.get("max_context_turns"),
            "statistics": stats,
        }

    except Exception as e:
        return JSONResponse({"error": "Failed to get model info", "details": str(e)}, status_code=500)


# Helper functions
async def _save_chat_message(request: Request, session_id: str, role: str, content: str, model_name: str):
    """Save chat message to database"""
    try:
        async with request.app.get_db_session() as session:
            message = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                model_name=model_name,
                metadata=json.dumps({}),
            )
            session.add(message)
            await session.commit()
    except Exception:
        # Don't fail the request if saving fails
        pass


# Include router
app.include_router(router, prefix="/api/v1")


# Add health endpoint
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "AI Chatbot"}


# Startup and shutdown
@app.on_startup
async def startup():
    """Initialize the chatbot application"""
    print("🤖 Starting AI Chatbot with nzrRest...")

    # Start context manager
    await context_manager.start()

    # Create database tables
    if app.db_manager:
        await app.db_manager.create_tables()

    # Register custom model class
    app.ai_registry.register_model_class("advanced_chat", AdvancedChatModel)

    # Add AI models with different personalities
    personalities = [
        (
            "friendly_chat",
            "friendly",
            "You are a friendly and enthusiastic AI assistant who loves to help and chat!",
        ),
        (
            "professional_chat",
            "professional",
            "You are a professional AI assistant focused on providing accurate and helpful information.",
        ),
        (
            "quirky_chat",
            "quirky",
            "You are a quirky and fun AI assistant with a unique personality and sense of humor!",
        ),
    ]

    for name, personality, system_prompt in personalities:
        await app.ai_registry.add_model(
            name=name,
            model_type="advanced_chat",
            config={
                "name": name,
                "version": "1.0.0",
                "provider": "nzrrest",
                "personality": personality,
                "system_prompt": system_prompt,
                "max_context_turns": 15,
            },
        )

        # Load the model
        await app.ai_registry.get_model(name).load_model()
        print(f"✅ Loaded {name} with {personality} personality")

    # Set default model
    await app.ai_registry.add_model(
        name="advanced_chat",
        model_type="advanced_chat",
        config={
            "name": "advanced_chat",
            "version": "1.0.0",
            "provider": "nzrrest",
            "personality": "helpful",
            "system_prompt": "You are a helpful AI assistant built with nzrRest framework. You're knowledgeable, friendly, and always ready to help!",
            "max_context_turns": 12,
        },
    )
    await app.ai_registry.get_model("advanced_chat").load_model()

    print("🎉 AI Chatbot ready!")
    print("📱 Try the chat API at: http://localhost:8001/api/v1/chat")


@app.on_shutdown
async def shutdown():
    """Cleanup on shutdown"""
    await context_manager.stop()
    print("🛑 AI Chatbot shutdown complete")


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Advanced AI Chatbot with nzrRest Framework")
    print("\nAvailable endpoints:")
    print("  POST /api/v1/chat - Chat with AI")
    print("  POST /api/v1/sessions - Create chat session")
    print("  GET  /api/v1/sessions/{id}/history - Get chat history")
    print("  GET  /api/v1/models/{name}/personality - Get model info")
    print("\nExample chat request:")
    print("  curl -X POST http://localhost:8001/api/v1/chat \\")
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"message": "Hello! Tell me about nzrRest framework"}\'')

    uvicorn.run("ai_chatbot:app", host="0.0.0.0", port=8001, reload=True, log_level="info")
