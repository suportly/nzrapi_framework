"""
API endpoints for {{ project_name }}
"""

import json
import uuid
from datetime import datetime
from typing import Optional

from config import settings
from models import ConversationHistory, ModelUsageStats

from nzrrest import JSONResponse, Request, Router
from nzrrest.ai.protocol import MCPError, MCPRequest, MCPResponse
from nzrrest.exceptions import ModelNotFoundError, ValidationError
from nzrrest.serializers import BaseSerializer, CharField, DictField

router = Router()


# Serializers
class MCPRequestSerializer(BaseSerializer):
    """Serializer for MCP requests"""

    context_id = CharField(required=False, allow_null=True)
    model_name = CharField(required=True)
    payload = DictField(required=True)
    metadata = DictField(required=False, default=dict)


class ChatRequestSerializer(BaseSerializer):
    """Serializer for chat requests"""

    message = CharField(required=True)
    context_id = CharField(required=False, allow_null=True)
    model_name = CharField(required=False, default="{{ default_model }}")


class TextAnalysisRequestSerializer(BaseSerializer):
    """Serializer for text analysis requests"""

    text = CharField(required=True)
    analysis_type = CharField(required=False, default="all")
    model_name = CharField(required=False, default="text_analyzer")


# Main MCP endpoint
@router.post("/mcp/{model_name}/predict")
async def mcp_predict(request: Request, model_name: str):
    """
    Main endpoint for MCP predictions with context management

    This endpoint follows the Model Context Protocol specification
    and integrates seamlessly with n8n workflows.
    """
    try:
        # Parse and validate request
        body = await request.json()
        serializer = MCPRequestSerializer(data=body)

        if not serializer.is_valid():
            return JSONResponse(
                {"error": "Invalid request", "details": serializer.errors},
                status_code=422,
            )

        # Create MCP request
        mcp_request = MCPRequest(model_name=model_name, **serializer.validated_data)

        # Get AI model
        ai_model = request.app.ai_registry.get_model(model_name)
        if not ai_model:
            return JSONResponse(
                {"error": f"Model '{model_name}' not found"}, status_code=404
            )

        # Retrieve context if provided
        context = {}
        if mcp_request.context_id:
            async with request.app.get_db_session() as session:
                conversation = await ConversationHistory.get_latest_by_context(
                    session, mcp_request.context_id
                )
                if conversation:
                    try:
                        context = json.loads(conversation.context_data or "{}")
                    except json.JSONDecodeError:
                        context = {}

        # Execute prediction
        start_time = datetime.utcnow()
        result = await ai_model.predict(mcp_request.payload, context)
        execution_time = (datetime.utcnow() - start_time).total_seconds()

        # Generate context ID if not provided
        context_id = mcp_request.context_id or str(uuid.uuid4())

        # Store conversation history
        async with request.app.get_db_session() as session:
            conversation = ConversationHistory(
                context_id=context_id,
                model_name=model_name,
                input_payload=json.dumps(mcp_request.payload),
                output_result=json.dumps(result),
                context_data=json.dumps(context),
                execution_time=execution_time,
                tokens_used=result.get("tokens_used"),
                success=True,
            )
            session.add(conversation)
            await session.commit()

        # Update usage stats
        await _update_usage_stats(
            request, model_name, execution_time, result.get("tokens_used", 0)
        )

        # Create MCP response
        response = MCPResponse(
            request_id=mcp_request.request_id,
            context_id=context_id,
            model_name=model_name,
            result=result,
            model_info=ai_model.model_info,
            execution_time=execution_time,
            tokens_used=result.get("tokens_used"),
        )

        return JSONResponse(response.dict())

    except ValidationError as e:
        return JSONResponse(
            {"error": "Validation error", "details": str(e)}, status_code=422
        )
    except ModelNotFoundError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except Exception as e:
        # Log error and store failed conversation
        if "mcp_request" in locals():
            async with request.app.get_db_session() as session:
                conversation = ConversationHistory(
                    context_id=mcp_request.context_id or "error",
                    model_name=model_name,
                    input_payload=json.dumps(mcp_request.payload),
                    output_result=json.dumps({"error": str(e)}),
                    success=False,
                )
                session.add(conversation)
                await session.commit()

        return JSONResponse(
            {"error": "Internal server error", "details": str(e)}, status_code=500
        )


# Convenience chat endpoint
@router.post("/chat")
async def chat(request: Request):
    """
    Simplified chat endpoint for conversational AI

    This endpoint provides an easy-to-use interface for chat applications.
    """
    try:
        body = await request.json()
        serializer = ChatRequestSerializer(data=body)

        if not serializer.is_valid():
            return JSONResponse(
                {"error": "Invalid request", "details": serializer.errors},
                status_code=422,
            )

        data = serializer.validated_data

        # Create MCP request
        mcp_request = MCPRequest(
            model_name=data["model_name"],
            context_id=data.get("context_id"),
            payload={"message": data["message"], "context_id": data.get("context_id")},
        )

        # Process through MCP endpoint
        request._json = mcp_request.dict()
        response = await mcp_predict(request, data["model_name"])

        # Extract and simplify response
        if response.status_code == 200:
            response_data = json.loads(response.body)
            return JSONResponse(
                {
                    "response": response_data["result"].get("response", ""),
                    "context_id": response_data["context_id"],
                    "model": response_data["model_name"],
                }
            )
        else:
            return response

    except Exception as e:
        return JSONResponse({"error": "Chat error", "details": str(e)}, status_code=500)


# Text analysis endpoint
@router.post("/analyze")
async def analyze_text(request: Request):
    """
    Text analysis endpoint for sentiment, keywords, entities, etc.
    """
    try:
        body = await request.json()
        serializer = TextAnalysisRequestSerializer(data=body)

        if not serializer.is_valid():
            return JSONResponse(
                {"error": "Invalid request", "details": serializer.errors},
                status_code=422,
            )

        data = serializer.validated_data

        # Create MCP request for text analysis
        mcp_request = MCPRequest(
            model_name=data["model_name"],
            payload={"text": data["text"], "analysis_type": data["analysis_type"]},
        )

        # Process through MCP endpoint
        request._json = mcp_request.dict()
        response = await mcp_predict(request, data["model_name"])

        return response

    except Exception as e:
        return JSONResponse(
            {"error": "Analysis error", "details": str(e)}, status_code=500
        )


# Model management endpoints
@router.get("/models")
async def list_models(request: Request):
    """List all available AI models"""
    try:
        models = request.app.ai_registry.list_models()
        return JSONResponse({"models": models})
    except Exception as e:
        return JSONResponse(
            {"error": "Failed to list models", "details": str(e)}, status_code=500
        )


@router.get("/models/{model_name}")
async def get_model_info(request: Request, model_name: str):
    """Get information about a specific model"""
    try:
        model = request.app.ai_registry.get_model(model_name)
        if not model:
            return JSONResponse(
                {"error": f"Model '{model_name}' not found"}, status_code=404
            )

        info = model.model_info
        stats = model.get_stats()

        return JSONResponse({"model_info": info, "statistics": stats})
    except Exception as e:
        return JSONResponse(
            {"error": "Failed to get model info", "details": str(e)}, status_code=500
        )


@router.get("/models/{model_name}/health")
async def model_health_check(request: Request, model_name: str):
    """Check health of a specific model"""
    try:
        model = request.app.ai_registry.get_model(model_name)
        if not model:
            return JSONResponse(
                {"error": f"Model '{model_name}' not found"}, status_code=404
            )

        health = await model.health_check()
        return JSONResponse(health.dict())
    except Exception as e:
        return JSONResponse(
            {"error": "Health check failed", "details": str(e)}, status_code=500
        )


# Conversation history endpoints
@router.get("/conversations/{context_id}")
async def get_conversation_history(request: Request, context_id: str):
    """Get conversation history for a context"""
    try:
        async with request.app.get_db_session() as session:
            conversations = await ConversationHistory.get_by_context_id(
                session, context_id
            )

            history = []
            for conv in conversations:
                history.append(
                    {
                        "id": conv.id,
                        "model_name": conv.model_name,
                        "input": json.loads(conv.input_payload),
                        "output": json.loads(conv.output_result),
                        "created_at": conv.created_at.isoformat(),
                        "execution_time": conv.execution_time,
                        "success": conv.success,
                    }
                )

            return JSONResponse(
                {
                    "context_id": context_id,
                    "conversation_count": len(history),
                    "history": history,
                }
            )
    except Exception as e:
        return JSONResponse(
            {"error": "Failed to get conversation history", "details": str(e)},
            status_code=500,
        )


# Usage statistics endpoint
@router.get("/stats")
async def get_usage_stats(request: Request):
    """Get usage statistics for all models"""
    try:
        async with request.app.get_db_session() as session:
            # Get overall stats
            stats = {}
            models = request.app.ai_registry.list_models()

            for model_info in models:
                model_name = model_info["name"]
                model_stats = await ModelUsageStats.get_stats_by_model(
                    session, model_name
                )
                stats[model_name] = [
                    {
                        "date": str(stat.date),
                        "requests": stat.requests,
                        "tokens": stat.tokens,
                        "avg_time": float(stat.avg_time or 0),
                        "errors": stat.errors,
                    }
                    for stat in model_stats
                ]

            return JSONResponse({"usage_statistics": stats})
    except Exception as e:
        return JSONResponse(
            {"error": "Failed to get usage stats", "details": str(e)}, status_code=500
        )


# Helper functions
async def _update_usage_stats(
    request: Request, model_name: str, execution_time: float, tokens_used: int
):
    """Update usage statistics for a model"""
    try:
        async with request.app.get_db_session() as session:
            # Find or create today's stats
            today = datetime.utcnow().date()

            from sqlalchemy import select

            stmt = select(ModelUsageStats).where(
                ModelUsageStats.model_name == model_name, ModelUsageStats.date >= today
            )
            result = await session.execute(stmt)
            stats = result.scalar_one_or_none()

            if stats:
                stats.requests_count += 1
                stats.total_tokens += tokens_used or 0
                stats.total_execution_time += execution_time
            else:
                stats = ModelUsageStats(
                    model_name=model_name,
                    date=datetime.utcnow(),
                    requests_count=1,
                    total_tokens=tokens_used or 0,
                    total_execution_time=execution_time,
                )
                session.add(stats)

            await session.commit()
    except Exception:
        # Don't fail the request if stats update fails
        pass
