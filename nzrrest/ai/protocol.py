"""
Model Context Protocol (MCP) schemas and utilities for nzrRest
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MCPRequest(BaseModel):
    """Standardized request for Model Context Protocol"""

    request_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique request identifier")
    context_id: Optional[str] = Field(None, description="Context session identifier")
    model_name: str = Field(..., description="Name of the AI model to use")
    payload: Dict[str, Any] = Field(..., description="Input data for the model")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Request timestamp")

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Model name cannot be empty")
        return v.strip()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "context_id": "conv_123",
                "model_name": "gpt-4",
                "payload": {"prompt": "Hello, how are you?", "max_tokens": 100},
                "metadata": {"user_id": "user_456", "session_id": "sess_789"},
            }
        }
    )


class MCPResponse(BaseModel):
    """Standardized response for Model Context Protocol"""

    request_id: str = Field(..., description="Original request identifier")
    context_id: str = Field(..., description="Context session identifier")
    model_name: str = Field(..., description="Name of the AI model used")
    result: Dict[str, Any] = Field(..., description="Model output/result")
    model_info: Optional[Dict[str, str]] = Field(None, description="Model metadata and info")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    tokens_used: Optional[int] = Field(None, description="Number of tokens consumed")
    cost: Optional[float] = Field(None, description="Cost of the request")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "request_id": "req_123",
                "context_id": "conv_123",
                "model_name": "gpt-4",
                "result": {
                    "response": "Hello! I'm doing well, thank you for asking.",
                    "confidence": 0.95,
                },
                "model_info": {"version": "gpt-4-0314", "provider": "openai"},
                "execution_time": 2.34,
                "tokens_used": 45,
            }
        }
    )


class MCPError(BaseModel):
    """Error response for MCP requests"""

    request_id: str = Field(..., description="Original request identifier")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "request_id": "req_123",
                "error_code": "MODEL_NOT_FOUND",
                "error_message": "The specified model 'invalid-model' was not found",
                "details": {"available_models": ["gpt-4", "gpt-3.5-turbo", "claude-3"]},
            }
        }
    )


class ContextData(BaseModel):
    """Context data structure for maintaining conversation state"""

    context_id: str = Field(..., description="Unique context identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Context creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Context metadata")
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Message history")
    state: Dict[str, Any] = Field(default_factory=dict, description="Persistent state data")
    ttl: Optional[int] = Field(None, description="Time to live in seconds")

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a message to the context"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        self.messages.append(message)
        self.updated_at = datetime.utcnow()

    def update_state(self, key: str, value: Any):
        """Update a state value"""
        self.state[key] = value
        self.updated_at = datetime.utcnow()

    def is_expired(self) -> bool:
        """Check if context has expired"""
        if self.ttl is None:
            return False

        age = (datetime.utcnow() - self.updated_at).total_seconds()
        return age > self.ttl

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "context_id": "conv_123",
                "metadata": {"user_id": "user_456", "conversation_type": "support"},
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello, I need help",
                        "timestamp": "2024-01-01T12:00:00Z",
                    },
                    {
                        "role": "assistant",
                        "content": "I'm here to help! What can I assist you with?",
                        "timestamp": "2024-01-01T12:00:05Z",
                    },
                ],
                "state": {"current_topic": "support_request", "escalation_level": 0},
                "ttl": 3600,
            }
        }
    )


class ModelHealth(BaseModel):
    """Health status for AI models"""

    model_name: str = Field(..., description="Model identifier")
    status: str = Field(..., description="Health status (healthy/degraded/unhealthy)")
    last_check: datetime = Field(default_factory=datetime.utcnow, description="Last health check")
    response_time: Optional[float] = Field(None, description="Average response time in seconds")
    success_rate: Optional[float] = Field(None, description="Success rate percentage")
    error_count: int = Field(default=0, description="Number of recent errors")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional health details")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ["healthy", "degraded", "unhealthy", "offline"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model_name": "gpt-4",
                "status": "healthy",
                "response_time": 2.1,
                "success_rate": 99.5,
                "error_count": 2,
                "details": {
                    "memory_usage": "45%",
                    "gpu_usage": "78%",
                    "queue_length": 3,
                },
            }
        }
    )


class BatchMCPRequest(BaseModel):
    """Batch request for processing multiple MCP requests"""

    batch_id: str = Field(default_factory=lambda: str(uuid4()), description="Batch identifier")
    requests: List[MCPRequest] = Field(..., description="List of MCP requests")
    parallel: bool = Field(default=True, description="Process requests in parallel")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Batch metadata")

    @field_validator("requests")
    @classmethod
    def validate_requests(cls, v):
        if not v:
            raise ValueError("Batch must contain at least one request")
        if len(v) > 100:  # Reasonable limit
            raise ValueError("Batch size cannot exceed 100 requests")
        return v


class BatchMCPResponse(BaseModel):
    """Batch response for multiple MCP requests"""

    batch_id: str = Field(..., description="Batch identifier")
    responses: List[Union[MCPResponse, MCPError]] = Field(..., description="List of responses")
    total_execution_time: Optional[float] = Field(None, description="Total batch execution time")
    success_count: int = Field(..., description="Number of successful requests")
    error_count: int = Field(..., description="Number of failed requests")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Batch metadata")
