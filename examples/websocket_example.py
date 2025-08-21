"""
WebSocket example demonstrating real-time features and AI streaming in nzrapi
"""

import asyncio
import json
from datetime import datetime
from typing import Any

from nzrapi import AIStreamingEndpoint, NzrApiApp, Router, WebSocket, WebSocketEndpoint, WebSocketManager
from nzrapi.responses import JSONResponse

# Create app with AI registry
app = NzrApiApp(title="WebSocket Demo", version="1.0.0")

# Initialize WebSocket manager
ws_manager = WebSocketManager()


# Regular HTTP routes
@app.get("/")
async def root(request):
    """Serve a simple WebSocket test page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>NzrApi WebSocket Demo</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; }
            .chat-box { border: 1px solid #ccc; height: 300px; overflow-y: scroll; padding: 10px; margin: 10px 0; }
            input[type="text"] { width: 70%; padding: 8px; }
            button { padding: 8px 16px; }
            .message { margin: 5px 0; padding: 5px; }
            .user { background-color: #e3f2fd; }
            .system { background-color: #f3e5f5; }
            .ai { background-color: #e8f5e8; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>NzrApi WebSocket Demo</h1>
            
            <h2>Echo Chat</h2>
            <div id="echo-messages" class="chat-box"></div>
            <input type="text" id="echo-input" placeholder="Type a message...">
            <button onclick="sendEchoMessage()">Send</button>
            <button onclick="connectEcho()">Connect</button>
            <button onclick="disconnectEcho()">Disconnect</button>
            
            <h2>AI Streaming Chat</h2>
            <div id="ai-messages" class="chat-box"></div>
            <input type="text" id="ai-input" placeholder="Ask AI something...">
            <button onclick="sendAIMessage()">Ask AI</button>
            <button onclick="connectAI()">Connect AI</button>
            <button onclick="disconnectAI()">Disconnect AI</button>
            
            <h2>Broadcast System</h2>
            <p>Status: <span id="broadcast-status">Disconnected</span></p>
            <button onclick="connectBroadcast()">Join Broadcast</button>
            <button onclick="disconnectBroadcast()">Leave Broadcast</button>
        </div>

        <script>
            let echoWs = null;
            let aiWs = null;
            let broadcastWs = null;

            function addMessage(containerId, message, type = 'system') {
                const container = document.getElementById(containerId);
                const div = document.createElement('div');
                div.className = `message ${type}`;
                div.innerHTML = `<small>${new Date().toLocaleTimeString()}</small><br>${message}`;
                container.appendChild(div);
                container.scrollTop = container.scrollHeight;
            }

            // Echo WebSocket
            function connectEcho() {
                if (echoWs) return;
                
                echoWs = new WebSocket('ws://localhost:8000/ws/echo');
                
                echoWs.onopen = function() {
                    addMessage('echo-messages', 'Connected to echo server', 'system');
                };
                
                echoWs.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    addMessage('echo-messages', data.echo || event.data, 'system');
                };
                
                echoWs.onclose = function() {
                    addMessage('echo-messages', 'Disconnected from echo server', 'system');
                    echoWs = null;
                };
            }

            function disconnectEcho() {
                if (echoWs) {
                    echoWs.close();
                    echoWs = null;
                }
            }

            function sendEchoMessage() {
                const input = document.getElementById('echo-input');
                if (echoWs && input.value) {
                    addMessage('echo-messages', input.value, 'user');
                    echoWs.send(JSON.stringify({message: input.value}));
                    input.value = '';
                }
            }

            // AI Streaming WebSocket
            function connectAI() {
                if (aiWs) return;
                
                aiWs = new WebSocket('ws://localhost:8000/ws/ai/default/session123');
                
                aiWs.onopen = function() {
                    addMessage('ai-messages', 'Connected to AI streaming', 'system');
                };
                
                aiWs.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    
                    if (data.type === 'chunk') {
                        // Streaming response chunk
                        const lastMessage = document.querySelector('#ai-messages .message:last-child');
                        if (lastMessage && lastMessage.classList.contains('ai')) {
                            lastMessage.innerHTML += data.content;
                        } else {
                            addMessage('ai-messages', data.content, 'ai');
                        }
                    } else {
                        addMessage('ai-messages', data.message || JSON.stringify(data), 'system');
                    }
                };
                
                aiWs.onclose = function() {
                    addMessage('ai-messages', 'Disconnected from AI', 'system');
                    aiWs = null;
                };
            }

            function disconnectAI() {
                if (aiWs) {
                    aiWs.close();
                    aiWs = null;
                }
            }

            function sendAIMessage() {
                const input = document.getElementById('ai-input');
                if (aiWs && input.value) {
                    addMessage('ai-messages', input.value, 'user');
                    aiWs.send(JSON.stringify({message: input.value}));
                    input.value = '';
                }
            }

            // Broadcast WebSocket
            function connectBroadcast() {
                if (broadcastWs) return;
                
                broadcastWs = new WebSocket('ws://localhost:8000/ws/broadcast');
                
                broadcastWs.onopen = function() {
                    document.getElementById('broadcast-status').textContent = 'Connected';
                };
                
                broadcastWs.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    console.log('Broadcast message:', data);
                };
                
                broadcastWs.onclose = function() {
                    document.getElementById('broadcast-status').textContent = 'Disconnected';
                    broadcastWs = null;
                };
            }

            function disconnectBroadcast() {
                if (broadcastWs) {
                    broadcastWs.close();
                    broadcastWs = null;
                }
            }

            // Enter key handlers
            document.getElementById('echo-input').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') sendEchoMessage();
            });
            
            document.getElementById('ai-input').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') sendAIMessage();
            });
        </script>
    </body>
    </html>
    """
    from nzrapi import HTMLResponse

    return HTMLResponse(html_content)


@app.get("/ws/status")
async def websocket_status(request):
    """Get WebSocket connection status"""
    info = ws_manager.get_connection_info()
    return JSONResponse(info)


# WebSocket routes
@app.websocket("/ws/echo")
async def websocket_echo(websocket: WebSocket, data: Any):
    """Simple echo WebSocket endpoint"""
    response = {
        "echo": data.get("message") if isinstance(data, dict) else str(data),
        "timestamp": datetime.utcnow().isoformat(),
        "type": "echo",
    }
    await ws_manager.send_personal_message(response, websocket)


class BroadcastEndpoint(WebSocketEndpoint):
    """WebSocket endpoint for broadcast messages"""

    async def on_connect(self, websocket: WebSocket, **path_params):
        """Handle new connection to broadcast channel"""
        await self.manager.connect(websocket, "broadcast")
        await self.manager.send_personal_message(
            {
                "type": "welcome",
                "message": "Connected to broadcast channel",
                "timestamp": datetime.utcnow().isoformat(),
            },
            websocket,
        )

    async def on_receive(self, websocket: WebSocket, data: Any):
        """Broadcast received message to all connected clients"""
        message = {
            "type": "broadcast",
            "message": data.get("message") if isinstance(data, dict) else str(data),
            "timestamp": datetime.utcnow().isoformat(),
            "from": f"client_{id(websocket)}",
        }
        await self.manager.send_to_group(message, "broadcast")


# Create custom AI streaming endpoint
class DemoAIEndpoint(AIStreamingEndpoint):
    """Demo AI streaming endpoint with custom behavior"""

    async def on_connect(self, websocket: WebSocket, **path_params):
        """Connect with custom welcome message"""
        session_id = path_params.get("session_id", "default")
        await self.manager.connect(websocket, session_id)

        await self.manager.send_personal_message(
            {
                "type": "connection",
                "message": f"🤖 Welcome to AI Streaming! Session: {session_id}",
                "session_id": session_id,
                "model": self.ai_model_name,
                "capabilities": ["text generation", "conversation", "streaming responses"],
            },
            websocket,
        )


# Add WebSocket routes to router
app.router.websocket_route("/ws/broadcast", BroadcastEndpoint(ws_manager))
app.router.websocket_route("/ws/ai/{model_name}/{session_id}", DemoAIEndpoint("default", ws_manager))


# Background task to send periodic broadcasts
async def periodic_broadcast():
    """Send periodic status updates to all broadcast connections"""
    while True:
        await asyncio.sleep(30)  # Every 30 seconds
        message = {
            "type": "system_broadcast",
            "message": "System heartbeat",
            "timestamp": datetime.utcnow().isoformat(),
            "connections": ws_manager.get_connection_count(),
            "uptime": "running",
        }
        await ws_manager.send_to_group(message, "broadcast")


@app.on_startup
async def startup_broadcast():
    """Start background broadcast task"""
    # Add a mock AI model for testing
    from nzrapi.ai.models import MockAIModel

    mock_config = {
        "name": "default",
        "mock_responses": {
            "Hello": "Hello! How can I help you today?",
            "How are you?": "I'm doing great! Thanks for asking. How are you?",
            "What can you do?": "I can help with various tasks like answering questions, having conversations, and providing information!",
        },
        "simulation_delay": 0.1,
    }

    # Register mock model
    model = MockAIModel(mock_config)
    await app.ai_registry.add_model("default", model)

    # Start periodic broadcast
    asyncio.create_task(periodic_broadcast())
    print("🚀 WebSocket demo started!")
    print("📡 Visit http://localhost:8000 for the demo interface")
    print("🔌 WebSocket endpoints:")
    print("   - ws://localhost:8000/ws/echo (Echo messages)")
    print("   - ws://localhost:8000/ws/broadcast (Broadcast channel)")
    print("   - ws://localhost:8000/ws/ai/default/session123 (AI streaming)")


if __name__ == "__main__":
    import uvicorn

    print("Starting WebSocket Demo...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
