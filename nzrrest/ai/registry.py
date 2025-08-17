"""
AI model registry for managing multiple models in nzrRest
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union

from ..exceptions import ModelNotFoundError
from .models import AIModel, MockAIModel
from .protocol import (
    BatchMCPRequest,
    BatchMCPResponse,
    MCPError,
    MCPRequest,
    MCPResponse,
    ModelHealth,
)

logger = logging.getLogger(__name__)


class AIRegistry:
    """Singleton registry for managing AI models"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.models: Dict[str, AIModel] = {}
            self.model_classes: Dict[str, Type[AIModel]] = {}
            self._lock = asyncio.Lock()
            self._health_cache: Dict[str, ModelHealth] = {}
            self._health_cache_ttl = 60  # seconds

            # Register default model types
            self.register_model_class("mock", MockAIModel)

            AIRegistry._initialized = True

    def register_model_class(self, model_type: str, model_class: Type[AIModel]):
        """Register a model class for a specific type

        Args:
            model_type: String identifier for the model type
            model_class: AIModel subclass
        """
        self.model_classes[model_type] = model_class
        logger.info(f"Registered model class '{model_type}': {model_class.__name__}")

    async def add_model(self, name: str, model_type: str, config: Dict[str, Any]) -> AIModel:
        """Add a new model to the registry

        Args:
            name: Unique name for the model
            model_type: Type of model (must be registered)
            config: Model configuration

        Returns:
            The created model instance

        Raises:
            ValueError: If model type is not registered or name already exists
        """
        async with self._lock:
            if name in self.models:
                raise ValueError(f"Model '{name}' already exists")

            if model_type not in self.model_classes:
                available_types = list(self.model_classes.keys())
                raise ValueError(f"Unknown model type '{model_type}'. Available: {available_types}")

            # Create model instance
            model_class = self.model_classes[model_type]
            config["name"] = name  # Ensure name is in config
            model = model_class(config)

            # Store in registry
            self.models[name] = model
            logger.info(f"Added model '{name}' of type '{model_type}'")

            return model

    async def remove_model(self, name: str) -> None:
        """Remove a model from the registry

        Args:
            name: Name of the model to remove

        Raises:
            ModelNotFoundError: If model doesn't exist
        """
        async with self._lock:
            if name not in self.models:
                raise ModelNotFoundError(f"Model '{name}' not found")

            # Unload model before removal
            model = self.models[name]
            if model.is_loaded:
                await model.unload_model()

            # Remove from registry
            del self.models[name]

            # Clear health cache
            if name in self._health_cache:
                del self._health_cache[name]

            logger.info(f"Removed model '{name}'")

    def get_model(self, name: str) -> Optional[AIModel]:
        """Get a model by name

        Args:
            name: Model name

        Returns:
            Model instance or None if not found
        """
        return self.models.get(name)

    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models with their info

        Returns:
            List of model information dictionaries
        """
        models_info = []
        for name, model in self.models.items():
            model_info = model.model_info.copy()
            model_info["name"] = name
            model_info["is_loaded"] = str(model.is_loaded)
            model_info["health_status"] = getattr(model, "_health_status", "unknown")
            models_info.append(model_info)

        return models_info

    async def load_models_from_config(self, config: Dict[str, Any]) -> None:
        """Load multiple models from configuration

        Args:
            config: Configuration dictionary with models
        """
        if "models" not in config:
            logger.warning("No models configuration found")
            return

        for model_config in config["models"]:
            try:
                name = model_config["name"]
                model_type = model_config["type"]
                model_config_data = model_config.get("config", {})

                await self.add_model(name, model_type, model_config_data)

                # Auto-load if specified
                if model_config.get("auto_load", False):
                    model = self.models[name]
                    await model.load_model()
                    logger.info(f"Auto-loaded model '{name}'")

            except Exception as e:
                logger.error(f"Failed to load model from config: {e}")

    async def health_check_all(self, use_cache: bool = True) -> Dict[str, ModelHealth]:
        """Perform health check on all models

        Args:
            use_cache: Whether to use cached health results

        Returns:
            Dictionary mapping model names to health status
        """
        health_results = {}

        for name, model in self.models.items():
            # Check cache first
            if use_cache and name in self._health_cache:
                cached_health = self._health_cache[name]
                cache_age = (datetime.utcnow() - cached_health.last_check).total_seconds()

                if cache_age < self._health_cache_ttl:
                    health_results[name] = cached_health
                    continue

            # Perform fresh health check
            try:
                health = await model.health_check()
                self._health_cache[name] = health
                health_results[name] = health
            except Exception as e:
                logger.error(f"Health check failed for model '{name}': {e}")
                health_results[name] = ModelHealth(
                    model_name=name,
                    status="unhealthy",
                    response_time=None,
                    success_rate=None,
                    error_count=1,
                    details={"error": str(e)},
                )

        return health_results

    async def predict(self, model_name: str, payload: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
        """Make prediction using specified model

        Args:
            model_name: Name of the model to use
            payload: Input data for prediction
            context: Optional context data

        Returns:
            Prediction result

        Raises:
            ModelNotFoundError: If model doesn't exist
        """
        model = self.get_model(model_name)
        if not model:
            raise ModelNotFoundError(f"Model '{model_name}' not found")

        return await model.predict(payload, context)

    async def process_mcp_request(self, request: MCPRequest, context: Optional[Dict] = None) -> MCPResponse:
        """Process an MCP request

        Args:
            request: MCP request object
            context: Optional context data

        Returns:
            MCP response object

        Raises:
            ModelNotFoundError: If model doesn't exist
        """
        model = self.get_model(request.model_name)
        if not model:
            raise ModelNotFoundError(f"Model '{request.model_name}' not found")

        return await model.process_request(request, context)

    async def process_batch_request(self, batch_request: BatchMCPRequest) -> BatchMCPResponse:
        """Process a batch of MCP requests

        Args:
            batch_request: Batch request object

        Returns:
            Batch response object
        """
        start_time = time.time()
        responses: List[Union[MCPResponse, MCPError]] = []
        success_count = 0
        error_count = 0

        if batch_request.parallel:
            # Process requests in parallel
            tasks = []
            for req in batch_request.requests:
                task = asyncio.create_task(self._safe_process_request(req))
                tasks.append(task)

            raw_responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions and convert to proper responses
            for raw_response in raw_responses:
                if isinstance(raw_response, BaseException):
                    # Convert exception to MCPError
                    responses.append(
                        MCPError(
                            request_id="unknown",
                            error_code="PROCESSING_ERROR",
                            error_message=str(raw_response),
                            details={"exception_type": type(raw_response).__name__},
                        )
                    )
                else:
                    responses.append(raw_response)
        else:
            # Process requests sequentially
            for req in batch_request.requests:
                response = await self._safe_process_request(req)
                responses.append(response)

        # Count successes and errors
        for response in responses:
            if isinstance(response, MCPResponse):
                success_count += 1
            else:
                error_count += 1

        total_execution_time = time.time() - start_time

        return BatchMCPResponse(
            batch_id=batch_request.batch_id,
            responses=responses,
            total_execution_time=total_execution_time,
            success_count=success_count,
            error_count=error_count,
            metadata=batch_request.metadata,
        )

    async def _safe_process_request(self, request: MCPRequest) -> Union[MCPResponse, MCPError]:
        """Safely process a single MCP request

        Args:
            request: MCP request object

        Returns:
            MCP response or error object
        """
        try:
            return await self.process_mcp_request(request)
        except Exception as e:
            return MCPError(
                request_id=request.request_id,
                error_code="PROCESSING_ERROR",
                error_message=str(e),
                details={"model_name": request.model_name},
            )

    async def warmup_all(self) -> Dict[str, bool]:
        """Warm up all models

        Returns:
            Dictionary mapping model names to success status
        """
        results = {}

        for name, model in self.models.items():
            try:
                await model.warmup()
                results[name] = True
                logger.info(f"Warmed up model '{name}'")
            except Exception as e:
                results[name] = False
                logger.error(f"Failed to warm up model '{name}': {e}")

        return results

    async def initialize(self) -> None:
        """Initialize the registry"""
        logger.info("AI Registry initialized")

    async def cleanup(self) -> None:
        """Clean up all models and resources"""
        for name, model in list(self.models.items()):
            try:
                if model.is_loaded:
                    await model.unload_model()
                logger.info(f"Cleaned up model '{name}'")
            except Exception as e:
                logger.error(f"Error cleaning up model '{name}': {e}")

        self.models.clear()
        self._health_cache.clear()
        logger.info("AI Registry cleaned up")
