/**
 * WebSocket Client - Clean Architecture Implementation
 * 
 * This client demonstrates proper WebSocket handling with:
 * - Connection management
 * - Message routing by type
 * - Error handling
 * - UI state management
 */

class WebSocketClient {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.messageHandlers = {
            'echo_response': this.handleEchoResponse.bind(this),
            'broadcast_message': this.handleBroadcastMessage.bind(this),
            'ai_stream': this.handleAIStream.bind(this),
            'ai_complete': this.handleAIComplete.bind(this),
            'error': this.handleError.bind(this)
        };
    }

    connect() {
        if (this.ws) {
            return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.addMessage('echoMessages', 'Connecting to WebSocket...', 'sent');
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            this.isConnected = true;
            this.updateConnectionStatus();
            this.addMessage('echoMessages', 'Connected successfully!', 'received');
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.routeMessage(message);
            } catch (error) {
                this.addMessage('echoMessages', `Parse error: ${error.message}`, 'error');
            }
        };

        this.ws.onclose = () => {
            this.isConnected = false;
            this.updateConnectionStatus();
            this.addMessage('echoMessages', 'Connection closed', 'error');
            this.ws = null;
        };

        this.ws.onerror = (error) => {
            this.addMessage('echoMessages', `WebSocket error: ${error}`, 'error');
        };
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }

    routeMessage(message) {
        const handler = this.messageHandlers[message.type];
        if (handler) {
            handler(message);
        } else {
            this.addMessage('echoMessages', `Unknown message type: ${message.type}`, 'error');
        }
    }

    sendMessage(message) {
        if (this.ws && this.isConnected) {
            this.ws.send(JSON.stringify(message));
            return true;
        }
        return false;
    }

    // Message Handlers
    handleEchoResponse(message) {
        this.addMessage('echoMessages', `Echo: ${message.message}`, 'received');
    }

    handleBroadcastMessage(message) {
        this.addMessage('broadcastMessages', `Broadcast: ${message.message}`, 'received');
    }

    handleAIStream(message) {
        if (message.chunk) {
            this.appendToLastMessage('aiMessages', message.chunk);
        }
    }

    handleAIComplete(message) {
        this.addMessage('aiMessages', `\\n[AI Response Complete]`, 'received');
    }

    handleError(message) {
        this.addMessage('echoMessages', `Error: ${message.message}`, 'error');
    }

    // UI Helper Methods
    updateConnectionStatus() {
        const statusEl = document.getElementById('status');
        const connectBtn = document.getElementById('connectBtn');
        const disconnectBtn = document.getElementById('disconnectBtn');
        const buttons = ['echoBtn', 'broadcastBtn', 'aiBtn'];

        if (this.isConnected) {
            statusEl.textContent = 'Connected';
            statusEl.className = 'status connected';
            connectBtn.disabled = true;
            disconnectBtn.disabled = false;
            buttons.forEach(id => document.getElementById(id).disabled = false);
        } else {
            statusEl.textContent = 'Disconnected';
            statusEl.className = 'status disconnected';
            connectBtn.disabled = false;
            disconnectBtn.disabled = true;
            buttons.forEach(id => document.getElementById(id).disabled = true);
        }
    }

    addMessage(containerId, text, type = 'received') {
        const container = document.getElementById(containerId);
        const messageEl = document.createElement('div');
        messageEl.className = `message ${type}`;
        messageEl.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
        container.appendChild(messageEl);
        container.scrollTop = container.scrollHeight;
    }

    appendToLastMessage(containerId, text) {
        const container = document.getElementById(containerId);
        const messages = container.querySelectorAll('.message');
        if (messages.length > 0) {
            const lastMessage = messages[messages.length - 1];
            lastMessage.textContent += text;
        } else {
            this.addMessage(containerId, text, 'received');
        }
        container.scrollTop = container.scrollHeight;
    }
}

// Global WebSocket client instance
const wsClient = new WebSocketClient();

// Global functions for UI interaction
function connect() {
    wsClient.connect();
}

function disconnect() {
    wsClient.disconnect();
}

function sendEcho() {
    const input = document.getElementById('echoInput');
    const message = input.value.trim();
    if (message) {
        const sent = wsClient.sendMessage({
            type: 'echo',
            message: message
        });
        if (sent) {
            wsClient.addMessage('echoMessages', `Sent: ${message}`, 'sent');
            input.value = '';
        }
    }
}

function sendBroadcast() {
    const input = document.getElementById('broadcastInput');
    const message = input.value.trim();
    if (message) {
        const sent = wsClient.sendMessage({
            type: 'broadcast',
            message: message
        });
        if (sent) {
            wsClient.addMessage('broadcastMessages', `Sent broadcast: ${message}`, 'sent');
            input.value = '';
        }
    }
}

function sendAIRequest() {
    const input = document.getElementById('aiInput');
    const question = input.value.trim();
    if (question) {
        const sent = wsClient.sendMessage({
            type: 'ai_request',
            message: question
        });
        if (sent) {
            wsClient.addMessage('aiMessages', `Question: ${question}`, 'sent');
            wsClient.addMessage('aiMessages', `AI: `, 'received'); // Placeholder for streaming response
            input.value = '';
        }
    }
}

// Handle Enter key in input fields
document.addEventListener('DOMContentLoaded', function() {
    ['echoInput', 'broadcastInput', 'aiInput'].forEach(id => {
        const input = document.getElementById(id);
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const buttonMap = {
                    'echoInput': sendEcho,
                    'broadcastInput': sendBroadcast,
                    'aiInput': sendAIRequest
                };
                buttonMap[id]();
            }
        });
    });
});