"""
Abstract AI model classes for nzrRest framework
"""

import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .protocol import MCPRequest, MCPResponse, ModelHealth


class AIModel(ABC):
    """Abstract base class for AI models in nzrRest"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the AI model with configuration

        Args:
            config: Model configuration dictionary
        """
        self.config = config
        self.name = config.get("name", "unknown_model")
        self.version = config.get("version", "1.0.0")
        self.provider = config.get("provider", "unknown")
        self.is_loaded = False
        self.last_execution_time: Optional[float] = None
        self.last_error: Optional[str] = None
        self.request_count = 0
        self.error_count = 0
        self.total_execution_time = 0.0

        # Health monitoring
        self._health_status = "offline"
        self._last_health_check = datetime.utcnow()

    @abstractmethod
    async def load_model(self) -> None:
        """Load the model into memory

        Raises:
            Exception: If model loading fails
        """
        pass

    @abstractmethod
    async def predict(self, payload: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute prediction with optional context

        Args:
            payload: Input data for prediction
            context: Optional context for stateful interactions

        Returns:
            Dictionary containing prediction results

        Raises:
            Exception: If prediction fails
        """
        pass

    @abstractmethod
    async def unload_model(self) -> None:
        """Remove model from memory to free resources

        Raises:
            Exception: If model unloading fails
        """
        pass

    @property
    @abstractmethod
    def model_info(self) -> Dict[str, str]:
        """Get model information and metadata

        Returns:
            Dictionary with model information
        """
        pass

    async def process_request(self, request: MCPRequest, context: Optional[Dict] = None) -> MCPResponse:
        """Process an MCP request and return response

        Args:
            request: MCP request object
            context: Optional context data

        Returns:
            MCP response object
        """
        start_time = time.time()

        try:
            # Ensure model is loaded
            if not self.is_loaded:
                await self.load_model()

            # Execute prediction
            result = await self.predict(request.payload, context)

            # Calculate execution time
            execution_time = time.time() - start_time
            self.last_execution_time = execution_time
            self.total_execution_time += execution_time
            self.request_count += 1

            # Create response
            response = MCPResponse(
                request_id=request.request_id,
                context_id=request.context_id or f"ctx_{request.request_id}",
                model_name=self.name,
                result=result,
                model_info=self.model_info,
                execution_time=execution_time,
                tokens_used=None,
                cost=None,
            )

            return response

        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            raise e

    async def health_check(self) -> ModelHealth:
        """Perform health check on the model

        Returns:
            ModelHealth object with current status
        """
        try:
            # Test prediction with minimal payload
            test_payload = {"test": True}
            start_time = time.time()

            if self.is_loaded:
                await self.predict(test_payload)
                response_time = time.time() - start_time
                status = "healthy"
            else:
                response_time = None
                status = "offline"

            # Calculate success rate
            if self.request_count > 0:
                success_rate = ((self.request_count - self.error_count) / self.request_count) * 100
            else:
                success_rate = 100.0

            # Determine status based on metrics
            if self.error_count > 10 or success_rate < 90:
                status = "degraded"
            elif not self.is_loaded:
                status = "offline"

            self._health_status = status
            self._last_health_check = datetime.utcnow()

            return ModelHealth(
                model_name=self.name,
                status=status,
                last_check=self._last_health_check,
                response_time=response_time,
                success_rate=success_rate,
                error_count=self.error_count,
                details={
                    "request_count": self.request_count,
                    "avg_execution_time": self.total_execution_time / max(self.request_count, 1),
                    "last_error": self.last_error,
                    "version": self.version,
                    "provider": self.provider,
                },
            )

        except Exception as e:
            self._health_status = "unhealthy"
            self.last_error = str(e)

            return ModelHealth(
                model_name=self.name,
                status="unhealthy",
                last_check=datetime.utcnow(),
                response_time=None,
                success_rate=None,
                error_count=self.error_count,
                details={"error": str(e)},
            )

    async def warmup(self) -> None:
        """Warm up the model with a test request"""
        if not self.is_loaded:
            await self.load_model()

        # Run a test prediction to warm up
        try:
            await self.predict({"warmup": True})
        except Exception:
            # Warmup failures are non-critical
            pass

    def get_stats(self) -> Dict[str, Any]:
        """Get model performance statistics

        Returns:
            Dictionary with performance metrics
        """
        return {
            "name": self.name,
            "version": self.version,
            "provider": self.provider,
            "is_loaded": self.is_loaded,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "success_rate": ((self.request_count - self.error_count) / max(self.request_count, 1)) * 100,
            "avg_execution_time": self.total_execution_time / max(self.request_count, 1),
            "last_execution_time": self.last_execution_time,
            "last_error": self.last_error,
            "health_status": self._health_status,
            "last_health_check": self._last_health_check.isoformat(),
        }


class MockAIModel(AIModel):
    """Mock AI model for testing and development"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mock_responses = config.get("mock_responses", {})
        self.simulation_delay = config.get("simulation_delay", 0.1)

    async def load_model(self) -> None:
        """Simulate model loading"""
        await asyncio.sleep(0.1)  # Simulate loading time
        self.is_loaded = True

    async def predict(self, payload: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
        """Mock prediction that returns predefined responses"""
        if not self.is_loaded:
            raise RuntimeError("Model not loaded")

        start_time = time.time()

        try:
            # Simulate processing time
            await asyncio.sleep(self.simulation_delay)

            # Update statistics
            self.request_count += 1

            # Check for specific mock responses
            if "prompt" in payload and payload["prompt"] in self.mock_responses:
                response = {"response": self.mock_responses[payload["prompt"]]}
            else:
                # Default response
                response = {
                    "response": f"Mock response to: {payload}",
                    "timestamp": datetime.utcnow().isoformat(),
                }

            # Always include common fields
            response["model"] = self.name
            response["context_used"] = context is not None

            # Update execution time
            execution_time = time.time() - start_time
            self.last_execution_time = execution_time
            self.total_execution_time += execution_time

            return response

        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            raise

    async def unload_model(self) -> None:
        """Simulate model unloading"""
        await asyncio.sleep(0.05)
        self.is_loaded = False

    @property
    def model_info(self) -> Dict[str, str]:
        """Get mock model information"""
        return {
            "name": self.name,
            "version": self.version,
            "provider": self.provider,
            "type": "mock",
            "description": "Mock AI model for testing",
            "capabilities": "text_generation,question_answering",
        }


class OpenAIModel(AIModel):
    """Example OpenAI model implementation"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.model_id = config.get("model_id", "gpt-3.5-turbo")
        self.client = None

    async def load_model(self) -> None:
        """Initialize OpenAI client"""
        try:
            # Note: This is a skeleton - you'd need to install openai package
            # import openai
            # self.client = openai.AsyncOpenAI(api_key=self.api_key)

            # For now, just set loaded status
            self.is_loaded = True
        except Exception as e:
            raise RuntimeError(f"Failed to load OpenAI model: {e}")

    async def predict(self, payload: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
        """Make prediction using OpenAI API"""
        if not self.is_loaded:
            raise RuntimeError("Model not loaded")

        # This is a skeleton implementation
        # In practice, you'd call the OpenAI API here

        prompt = payload.get("prompt", "")
        max_tokens = payload.get("max_tokens", 100)

        # Simulate API call
        await asyncio.sleep(0.5)

        return {
            "response": f"OpenAI response to: {prompt}",
            "model": self.model_id,
            "tokens_used": len(prompt.split()) + 20,
            "finish_reason": "stop",
        }

    async def unload_model(self) -> None:
        """Clean up OpenAI client"""
        self.client = None
        self.is_loaded = False

    @property
    def model_info(self) -> Dict[str, str]:
        """Get OpenAI model information"""
        return {
            "name": self.name,
            "version": self.version,
            "provider": "openai",
            "model_id": self.model_id,
            "type": "language_model",
            "description": f"OpenAI {self.model_id} model",
            "capabilities": "text_generation,chat,completion",
        }
