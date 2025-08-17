# {{ project_name }}

{{ description }}

This project is built with the **nzrRest Framework** - a modern Python framework for building AI APIs with native Model Context Protocol (MCP) support.

## Features

- 🤖 **AI Model Integration**: Built-in support for multiple AI models
- 🔄 **Model Context Protocol**: Native MCP implementation for n8n integration
- 🚀 **High Performance**: Async/await throughout with ASGI support
- 📊 **Context Management**: Persistent conversation contexts
- 🛡️ **Production Ready**: Rate limiting, authentication, monitoring
- 🗄️ **Database Integration**: SQLAlchemy async with migrations
- 📈 **Usage Analytics**: Built-in usage tracking and statistics
- 🐳 **Docker Ready**: Production-ready containerization

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables (optional)
cp .env.example .env
```

### 2. Configuration

Update `config.py` with your settings:

```python
# Database configuration
DATABASE_URL = "sqlite+aiosqlite:///./{{ project_name }}.db"

# AI model configuration  
AI_MODELS_CONFIG = {
    "models": [
        {
            "name": "{{ default_model }}",
            "type": "{{ default_model }}",
            "auto_load": True,
            "config": {
                # Add your model configuration here
            }
        }
    ]
}
```

### 3. Run the Server

```bash
# Development mode with auto-reload
python main.py

# Or using nzrrest CLI
nzrrest run --reload

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Main MCP Endpoint

```http
POST /api/v1/mcp/{model_name}/predict
```

**Request:**
```json
{
  "context_id": "optional-context-id",
  "payload": {
    "message": "Hello, how are you?"
  },
  "metadata": {
    "user_id": "user123"
  }
}
```

**Response:**
```json
{
  "request_id": "req_123",
  "context_id": "ctx_456", 
  "model_name": "{{ default_model }}",
  "result": {
    "response": "Hello! I'm doing well, thank you for asking."
  },
  "execution_time": 0.234
}
```

### Chat Endpoint (Simplified)

```http
POST /api/v1/chat
```

```json
{
  "message": "Hello!",
  "context_id": "optional",
  "model_name": "{{ default_model }}"
}
```

### Model Management

```http
GET /api/v1/models                    # List all models
GET /api/v1/models/{model_name}       # Get model info
GET /api/v1/models/{model_name}/health # Health check
```

### Conversation History

```http
GET /api/v1/conversations/{context_id} # Get conversation history
```

### Usage Statistics

```http
GET /api/v1/stats                     # Get usage statistics
```

## n8n Integration

This API is designed for seamless integration with n8n workflows:

1. **HTTP Request Node**: Use the MCP endpoint for AI predictions
2. **Context Management**: Maintain conversation state across workflow runs
3. **Error Handling**: Robust error responses for workflow logic
4. **Batch Processing**: Support for processing multiple requests

### Example n8n Workflow

```json
{
  "nodes": [
    {
      "name": "AI Chat",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://your-api.com/api/v1/mcp/{{ default_model }}/predict",
        "method": "POST",
        "body": {
          "context_id": "{{ "{{" }} $('previous').first().json.context_id {{ "}}" }}",
          "payload": {
            "message": "{{ "{{" }} $json.user_message {{ "}}" }}"
          }
        }
      }
    }
  ]
}
```

## Database Migrations

```bash
# Generate migration
nzrrest migrate -m "Add new table"

# Run migrations
nzrrest migrate --upgrade

# Rollback migration
nzrrest migrate --downgrade -1
```

## Docker Deployment

```bash
# Build image
docker build -t {{ project_name }} .

# Run container
docker run -p 8000:8000 -e DATABASE_URL="your-db-url" {{ project_name }}

# Docker Compose (recommended)
docker-compose up -d
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `DATABASE_URL` | Database connection URL | SQLite local file |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `RATE_LIMIT_PER_MINUTE` | Rate limit per minute | `60` |
| `RATE_LIMIT_PER_HOUR` | Rate limit per hour | `1000` |
{% if include_auth %}
| `SECRET_KEY` | JWT secret key | Required for auth |
| `OPENAI_API_KEY` | OpenAI API key | Required for OpenAI models |
| `ANTHROPIC_API_KEY` | Anthropic API key | Required for Claude models |
{% endif %}

## Model Types

This project supports multiple AI model types:

- **Mock Models**: For development and testing
- **OpenAI Models**: GPT-3.5, GPT-4, etc.
- **Anthropic Models**: Claude-3, etc.
- **Custom Models**: Implement your own AI models

### Adding Custom Models

1. Create a new model class inheriting from `AIModel`:

```python
from nzrrest.ai.models import AIModel

class MyCustomModel(AIModel):
    async def load_model(self):
        # Load your model
        pass
    
    async def predict(self, payload, context=None):
        # Make predictions
        return {"response": "My custom response"}
```

2. Register the model type:

```python
app.ai_registry.register_model_class('custom', MyCustomModel)
```

3. Add to configuration:

```python
AI_MODELS_CONFIG["models"].append({
    "name": "my_model",
    "type": "custom", 
    "auto_load": True,
    "config": {}
})
```

## Monitoring

- **Health Check**: `GET /health`
- **Metrics**: `GET /metrics` 
- **Model Health**: `GET /api/v1/models/{name}/health`
- **Usage Stats**: `GET /api/v1/stats`

## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest

# With coverage
pytest --cov=.
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

- **Documentation**: [nzrRest Framework Docs](https://nzrrest.readthedocs.io)
- **Issues**: [GitHub Issues](https://github.com/yourusername/nzrrest/issues)
- **Community**: [Discord Server](https://discord.gg/nzrrest)

---

Built with ❤️ using [nzrRest Framework](https://github.com/yourusername/nzrrest)