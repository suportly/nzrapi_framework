"""
Tests for AI models and MCP protocol
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from nzrrest.ai.context import ContextConfig, ContextManager
from nzrrest.ai.models import AIModel, MockAIModel
from nzrrest.ai.protocol import ContextData, MCPRequest, MCPResponse
from nzrrest.ai.registry import AIRegistry


class TestMockAIModel:
    """Test MockAIModel implementation"""

    @pytest.fixture
    def mock_model(self):
        """Create mock AI model"""
        config = {
            "name": "test_model",
            "version": "1.0.0",
            "provider": "test",
            "mock_responses": {"hello": "Hello there!", "test": "Test response"},
            "simulation_delay": 0.01,  # Very fast for tests
        }
        return MockAIModel(config)

    @pytest.mark.asyncio
    async def test_model_loading(self, mock_model):
        """Test model loading and unloading"""
        assert not mock_model.is_loaded

        await mock_model.load_model()
        assert mock_model.is_loaded

        await mock_model.unload_model()
        assert not mock_model.is_loaded

    @pytest.mark.asyncio
    async def test_model_prediction(self, mock_model):
        """Test model prediction"""
        await mock_model.load_model()

        # Test with predefined response
        result = await mock_model.predict({"prompt": "hello"})
        assert "response" in result
        assert result["response"] == "Hello there!"

        # Test with generic response
        result = await mock_model.predict({"prompt": "unknown"})
        assert "response" in result
        assert "Mock response to:" in result["response"]

    @pytest.mark.asyncio
    async def test_model_with_context(self, mock_model):
        """Test model prediction with context"""
        await mock_model.load_model()

        context = {"user_id": "123", "session": "abc"}
        result = await mock_model.predict({"prompt": "test"}, context)

        assert result["context_used"] is True
        assert "model" in result
        assert result["model"] == "test_model"

    @pytest.mark.asyncio
    async def test_model_stats(self, mock_model):
        """Test model statistics"""
        await mock_model.load_model()

        # Make some predictions
        await mock_model.predict({"prompt": "test1"})
        await mock_model.predict({"prompt": "test2"})

        stats = mock_model.get_stats()
        assert stats["request_count"] == 2
        assert stats["error_count"] == 0
        assert stats["success_rate"] == 100.0
        assert stats["is_loaded"] is True

    @pytest.mark.asyncio
    async def test_model_health_check(self, mock_model):
        """Test model health check"""
        await mock_model.load_model()

        health = await mock_model.health_check()
        assert health.model_name == "test_model"
        assert health.status == "healthy"
        assert health.response_time is not None

    def test_model_info(self, mock_model):
        """Test model info property"""
        info = mock_model.model_info
        assert info["name"] == "test_model"
        assert info["version"] == "1.0.0"
        assert info["provider"] == "test"
        assert info["type"] == "mock"

    @pytest.mark.asyncio
    async def test_mcp_request_processing(self, mock_model):
        """Test MCP request processing"""
        await mock_model.load_model()

        request = MCPRequest(
            model_name="test_model",
            payload={"prompt": "hello"},
            context_id="test_context",
        )

        response = await mock_model.process_request(request)

        assert isinstance(response, MCPResponse)
        assert response.request_id == request.request_id
        assert response.context_id == "test_context"
        assert response.model_name == "test_model"
        assert "response" in response.result


class TestAIRegistry:
    """Test AIRegistry functionality"""

    @pytest.fixture
    def registry(self):
        """Create fresh AI registry"""
        # Clear singleton instance for testing
        AIRegistry._instance = None
        AIRegistry._initialized = False
        return AIRegistry()

    @pytest.mark.asyncio
    async def test_registry_initialization(self, registry):
        """Test registry initialization"""
        await registry.initialize()
        assert "mock" in registry.model_classes

    @pytest.mark.asyncio
    async def test_model_registration(self, registry):
        """Test model registration and retrieval"""
        await registry.initialize()

        # Add a mock model
        config = {"name": "test_model", "mock_responses": {"hello": "Hi!"}}

        model = await registry.add_model("test_model", "mock", config)
        assert model is not None
        assert model.name == "test_model"

        # Retrieve the model
        retrieved = registry.get_model("test_model")
        assert retrieved is model

        # List models
        models = registry.list_models()
        assert len(models) == 1
        assert models[0]["name"] == "test_model"

    @pytest.mark.asyncio
    async def test_model_removal(self, registry):
        """Test model removal"""
        await registry.initialize()

        # Add model
        await registry.add_model("test_model", "mock", {"name": "test_model"})
        assert registry.get_model("test_model") is not None

        # Remove model
        await registry.remove_model("test_model")
        assert registry.get_model("test_model") is None

    @pytest.mark.asyncio
    async def test_load_models_from_config(self, registry):
        """Test loading models from configuration"""
        await registry.initialize()

        config = {
            "models": [
                {
                    "name": "model1",
                    "type": "mock",
                    "auto_load": True,
                    "config": {"name": "model1"},
                },
                {
                    "name": "model2",
                    "type": "mock",
                    "auto_load": False,
                    "config": {"name": "model2"},
                },
            ]
        }

        await registry.load_models_from_config(config)

        assert registry.get_model("model1") is not None
        assert registry.get_model("model2") is not None

        # Check auto-load status
        model1 = registry.get_model("model1")
        model2 = registry.get_model("model2")
        assert model1.is_loaded is True
        assert model2.is_loaded is False

    @pytest.mark.asyncio
    async def test_health_check_all(self, registry):
        """Test health check for all models"""
        await registry.initialize()

        # Add models
        await registry.add_model("model1", "mock", {"name": "model1"})
        await registry.add_model("model2", "mock", {"name": "model2"})

        # Load models
        await registry.get_model("model1").load_model()
        await registry.get_model("model2").load_model()

        # Health check
        health_results = await registry.health_check_all()

        assert "model1" in health_results
        assert "model2" in health_results
        assert health_results["model1"].status == "healthy"
        assert health_results["model2"].status == "healthy"

    @pytest.mark.asyncio
    async def test_predict_through_registry(self, registry):
        """Test making predictions through registry"""
        await registry.initialize()

        # Add and load model
        await registry.add_model(
            "test_model",
            "mock",
            {"name": "test_model", "mock_responses": {"hello": "Hi from registry!"}},
        )
        await registry.get_model("test_model").load_model()

        # Make prediction
        result = await registry.predict("test_model", {"prompt": "hello"})
        assert result["response"] == "Hi from registry!"


class TestMCPProtocol:
    """Test MCP protocol schemas"""

    def test_mcp_request_creation(self):
        """Test MCP request creation and validation"""
        request = MCPRequest(
            model_name="test_model",
            payload={"prompt": "Hello"},
            context_id="test_context",
        )

        assert request.model_name == "test_model"
        assert request.payload == {"prompt": "Hello"}
        assert request.context_id == "test_context"
        assert request.request_id is not None

    def test_mcp_response_creation(self):
        """Test MCP response creation"""
        response = MCPResponse(
            request_id="req_123",
            context_id="ctx_456",
            model_name="test_model",
            result={"response": "Hello there!"},
        )

        assert response.request_id == "req_123"
        assert response.context_id == "ctx_456"
        assert response.model_name == "test_model"
        assert response.result == {"response": "Hello there!"}

    def test_context_data(self):
        """Test ContextData functionality"""
        context = ContextData(context_id="test_context", ttl=3600)

        # Add messages
        context.add_message("user", "Hello")
        context.add_message("assistant", "Hi there!")

        assert len(context.messages) == 2
        assert context.messages[0]["role"] == "user"
        assert context.messages[1]["role"] == "assistant"

        # Update state
        context.update_state("mood", "happy")
        assert context.state["mood"] == "happy"


class TestContextManager:
    """Test ContextManager functionality"""

    @pytest.fixture
    def context_manager(self):
        """Create context manager for testing"""
        config = ContextConfig(
            default_ttl=60,  # 1 minute for fast tests
            cleanup_interval=10,  # 10 seconds for stable tests
        )
        return ContextManager(config)

    @pytest.mark.asyncio
    async def test_context_creation(self, context_manager):
        """Test context creation and retrieval"""
        context_id = f"test_context_{uuid.uuid4().hex[:8]}"
        await context_manager.start()
        try:
            # Create context
            context = await context_manager.create_context(context_id, metadata={"user_id": "123"})

            assert context.context_id == context_id
            assert context.metadata["user_id"] == "123"

            # Retrieve context
            retrieved = await context_manager.get_context(context_id)
            assert retrieved is not None
            assert retrieved.context_id == context_id
        finally:
            await context_manager.stop()

    @pytest.mark.asyncio
    async def test_context_messages(self, context_manager):
        """Test adding messages to context"""
        context_id = f"test_context_{uuid.uuid4().hex[:8]}"
        await context_manager.start()
        try:
            await context_manager.create_context(context_id)

            # Add messages
            success = await context_manager.add_message(context_id, "user", "Hello")
            assert success is True

            success = await context_manager.add_message(context_id, "assistant", "Hi there!")
            assert success is True

            # Check messages
            context = await context_manager.get_context(context_id)
            assert len(context.messages) == 2
        finally:
            await context_manager.stop()

    @pytest.mark.asyncio
    async def test_context_state_updates(self, context_manager):
        """Test context state updates"""
        context_id = f"test_context_{uuid.uuid4().hex[:8]}"
        await context_manager.start()
        try:
            await context_manager.create_context(context_id)

            # Update state
            success = await context_manager.update_state(context_id, "step", "greeting")
            assert success is True

            # Check state
            context = await context_manager.get_context(context_id)
            assert context.state["step"] == "greeting"
        finally:
            await context_manager.stop()

    @pytest.mark.asyncio
    async def test_context_expiration(self, context_manager):
        """Test context expiration"""
        context_id = f"test_context_{uuid.uuid4().hex[:8]}"
        await context_manager.start()
        try:
            # Create context with very short TTL
            context = await context_manager.create_context(context_id, ttl=1)  # 1 second

            # Context should exist initially
            retrieved = await context_manager.get_context(context_id)
            assert retrieved is not None

            # Wait for expiration
            await asyncio.sleep(2)

            # Context should be expired
            retrieved = await context_manager.get_context(context_id)
            assert retrieved is None
        finally:
            await context_manager.stop()

    def test_context_manager_stats(self, context_manager):
        """Test context manager statistics"""
        stats = context_manager.get_stats()

        assert "contexts_created" in stats
        assert "contexts_accessed" in stats
        assert "active_contexts" in stats
        assert "max_contexts" in stats
