"""
WebSocket classes for NzrApi framework

This module provides abstractions over Starlette WebSockets,
so users don't need to import from Starlette directly.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set, Union
from uuid import uuid4

from starlette.websockets import WebSocket as StarletteWebSocket
from starlette.websockets import WebSocketDisconnect as StarletteWebSocketDisconnect


# Re-export WebSocket classes with abstractions
class WebSocket(StarletteWebSocket):
    """WebSocket class - abstraction over Starlette WebSocket"""

    pass


class WebSocketDisconnect(StarletteWebSocketDisconnect):
    """WebSocket disconnect exception - abstraction over Starlette WebSocketDisconnect"""

    pass


class WebSocketManager:
    """WebSocket connection manager for handling multiple connections"""

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.groups: Dict[str, Set[str]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def connect(self, websocket: WebSocket, connection_id: str = None) -> str:
        """Add a WebSocket connection"""
        if connection_id is None:
            connection_id = str(uuid4())

        self.connections[connection_id] = websocket
        self.logger.info(f"WebSocket connected: {connection_id}")
        return connection_id

    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection"""
        if connection_id in self.connections:
            del self.connections[connection_id]
            # Remove from all groups
            for group_name, group_connections in self.groups.items():
                group_connections.discard(connection_id)
            self.logger.info(f"WebSocket disconnected: {connection_id}")

    def join_group(self, connection_id: str, group_name: str):
        """Add connection to a group"""
        if group_name not in self.groups:
            self.groups[group_name] = set()
        self.groups[group_name].add(connection_id)
        self.logger.debug(f"Connection {connection_id} joined group {group_name}")

    def leave_group(self, connection_id: str, group_name: str):
        """Remove connection from a group"""
        if group_name in self.groups:
            self.groups[group_name].discard(connection_id)
            if not self.groups[group_name]:
                del self.groups[group_name]
        self.logger.debug(f"Connection {connection_id} left group {group_name}")

    async def send_personal_message(self, connection_id: str, message: Union[str, dict]):
        """Send message to specific connection"""
        if connection_id in self.connections:
            websocket = self.connections[connection_id]
            try:
                if isinstance(message, dict):
                    await websocket.send_json(message)
                else:
                    await websocket.send_text(message)
            except Exception as e:
                self.logger.error(f"Error sending message to {connection_id}: {e}")
                self.disconnect(connection_id)

    async def broadcast_to_group(self, group_name: str, message: Union[str, dict]):
        """Broadcast message to all connections in a group"""
        if group_name in self.groups:
            connections_to_remove = []
            for connection_id in self.groups[group_name]:
                if connection_id in self.connections:
                    websocket = self.connections[connection_id]
                    try:
                        if isinstance(message, dict):
                            await websocket.send_json(message)
                        else:
                            await websocket.send_text(message)
                    except Exception as e:
                        self.logger.error(f"Error broadcasting to {connection_id}: {e}")
                        connections_to_remove.append(connection_id)

            # Remove failed connections
            for connection_id in connections_to_remove:
                self.disconnect(connection_id)

    async def broadcast(self, message: Union[str, dict]):
        """Broadcast message to all connections"""
        connections_to_remove = []
        for connection_id, websocket in self.connections.items():
            try:
                if isinstance(message, dict):
                    await websocket.send_json(message)
                else:
                    await websocket.send_text(message)
            except Exception as e:
                self.logger.error(f"Error broadcasting to {connection_id}: {e}")
                connections_to_remove.append(connection_id)

        # Remove failed connections
        for connection_id in connections_to_remove:
            self.disconnect(connection_id)

    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.connections)

    def get_group_size(self, group_name: str) -> int:
        """Get number of connections in a group"""
        return len(self.groups.get(group_name, set()))


class WebSocketEndpoint:
    """Base WebSocket endpoint class"""

    def __init__(self, manager: WebSocketManager = None):
        self.manager = manager or default_manager
        self.logger = logging.getLogger(self.__class__.__name__)

    async def on_connect(self, websocket: WebSocket) -> str:
        """Handle new WebSocket connection"""
        await websocket.accept()
        connection_id = self.manager.connect(websocket)
        return connection_id

    async def on_disconnect(self, connection_id: str, close_code: int) -> None:
        """Handle WebSocket disconnection"""
        self.manager.disconnect(connection_id)

    async def on_receive(self, websocket: WebSocket, connection_id: str, data: Union[str, bytes]) -> None:
        """Handle received WebSocket message"""
        pass

    async def __call__(self, websocket: WebSocket):
        """WebSocket endpoint handler"""
        connection_id = await self.on_connect(websocket)

        try:
            while True:
                data = await websocket.receive()
                if data["type"] == "websocket.receive":
                    message_data = data.get("text") or data.get("bytes")
                    await self.on_receive(websocket, connection_id, message_data)
                elif data["type"] == "websocket.disconnect":
                    break

        except WebSocketDisconnect as e:
            await self.on_disconnect(connection_id, e.code)
        except Exception as e:
            self.logger.error(f"WebSocket error: {e}")
            try:
                await websocket.close(code=1011)  # Internal error
            except Exception:
                pass
            self.manager.disconnect(connection_id)


class AIStreamingEndpoint(WebSocketEndpoint):
    """WebSocket endpoint optimized for AI streaming responses"""

    def __init__(self, ai_model=None, manager: WebSocketManager = None):
        super().__init__(manager)
        self.ai_model = ai_model

    async def on_receive(self, websocket: WebSocket, connection_id: str, data: Union[str, bytes]):
        """Handle AI streaming request"""
        try:
            if isinstance(data, str):
                message = json.loads(data)
            else:
                message = json.loads(data.decode())

            if message.get("type") == "ai_request" and self.ai_model:
                prompt = message.get("message", "")
                await self.stream_ai_response(websocket, connection_id, prompt)
            else:
                await websocket.send_json(
                    {"type": "error", "message": "Invalid message format or AI model not configured"}
                )

        except json.JSONDecodeError:
            await websocket.send_json({"type": "error", "message": "Invalid JSON format"})
        except Exception as e:
            self.logger.error(f"Error processing AI request: {e}")
            await websocket.send_json({"type": "error", "message": "Internal server error"})

    async def stream_ai_response(self, websocket: WebSocket, connection_id: str, prompt: str) -> None:
        """Stream AI response in chunks"""
        try:
            # This is a mock implementation - integrate with your AI model
            response_chunks = [
                "This ",
                "is ",
                "a ",
                "mock ",
                "AI ",
                "streaming ",
                "response. ",
                "In ",
                "a ",
                "real ",
                "implementation, ",
                "you ",
                "would ",
                "connect ",
                "to ",
                "your ",
                "AI ",
                "model ",
                "here.",
            ]

            for chunk in response_chunks:
                await websocket.send_json({"type": "ai_stream", "chunk": chunk})
                await asyncio.sleep(0.1)  # Simulate streaming delay

            await websocket.send_json({"type": "ai_complete", "message": "AI response complete"})

        except Exception as e:
            self.logger.error(f"Error streaming AI response: {e}")
            await websocket.send_json({"type": "error", "message": "Error generating AI response"})


# Default global manager instance
default_manager = WebSocketManager()


# Utility functions
async def websocket_endpoint(websocket: WebSocket):
    """Simple WebSocket endpoint for basic usage"""
    await websocket.accept()
    connection_id = default_manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # Echo the message back
            await websocket.send_text(f"Echo: {data}")

    except WebSocketDisconnect:
        default_manager.disconnect(connection_id)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        default_manager.disconnect(connection_id)
