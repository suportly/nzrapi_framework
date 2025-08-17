# nzrRest Framework

<div align="center">

🤖 **Modern Async Python Framework for AI APIs with Native MCP Support**

[![PyPI version](https://badge.fury.io/py/nzrrest.svg)](https://badge.fury.io/py/nzrrest)
[![Python Support](https://img.shields.io/pypi/pyversions/nzrrest.svg)](https://pypi.org/project/nzrrest/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://github.com/nzrrest/nzrrest/workflows/Tests/badge.svg)](https://github.com/nzrrest/nzrrest/actions)
[![Coverage](https://codecov.io/gh/nzrrest/nzrrest/branch/main/graph/badge.svg)](https://codecov.io/gh/nzrrest/nzrrest)

[**Documentation**](https://nzrrest.readthedocs.io) | [**Examples**](examples/) | [**n8n Integration**](examples/n8n_integration/) | [**Contributing**](CONTRIBUTING.md)

</div>

---

## ✨ What is nzrRest?

**nzrRest** is a powerful, production-ready Python framework specifically designed for building AI-powered APIs. It combines the best of modern web frameworks with specialized features for AI model integration, making it the perfect choice for developers who want to build scalable AI services with minimal complexity.

### 🎯 Key Features

- 🤖 **Native AI Model Integration** - First-class support for multiple AI providers and custom models
- 🔄 **Model Context Protocol (MCP)** - Built-in MCP implementation for seamless n8n integration
- ⚡ **High Performance** - Async/await throughout with ASGI compliance 
- 📊 **Context Management** - Persistent conversation contexts with automatic cleanup
- 🛡️ **Production Ready** - Rate limiting, authentication, monitoring, and error handling
- 🗄️ **Database Integration** - SQLAlchemy async with automatic migrations
- 🎨 **DRF-Inspired Serializers** - Familiar, powerful data validation and transformation
- 🚀 **Auto-Generation** - CLI tools for rapid project scaffolding
- 🐳 **Cloud Native** - Docker support with production configurations

## 🚀 Quick Start

### Installation

```bash
pip install nzrrest
```

### Create Your First AI API

```bash
# Create a new project
nzrrest new my-ai-api

# Navigate to project
cd my-ai-api

# Run the development server
nzrrest run --reload
```

Your AI API is now running at `http://localhost:8000`! 🎉

### Hello World Example

```python
from nzrrest import NzrRestApp, Router

app = NzrRestApp(title="My AI API")
router = Router()

@router.post("/chat")
async def chat(request):
    data = await request.json()
    
    # Use built-in AI model
    model = request.app.ai_registry.get_model("default")
    result = await model.predict({"message": data["message"]})
    
    return {"response": result["response"]}

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 🤖 AI Model Integration

nzrRest makes it incredibly easy to work with AI models:

```python
from nzrrest.ai.models import AIModel

class MyCustomModel(AIModel):
    async def load_model(self):
        # Load your model (PyTorch, HuggingFace, OpenAI, etc.)
        self.model = load_my_model()
        self.is_loaded = True
    
    async def predict(self, payload, context=None):
        # Make predictions with optional context
        result = self.model.generate(payload["prompt"])
        return {"response": result}

# Register and use
app.ai_registry.register_model_class("custom", MyCustomModel)
await app.ai_registry.add_model("my_model", "custom", config={...})
```

### Supported AI Providers

- ✅ **OpenAI** (GPT-3.5, GPT-4, etc.)
- ✅ **Anthropic** (Claude models)
- ✅ **HuggingFace** (Transformers, Inference API)
- ✅ **Custom Models** (PyTorch, TensorFlow, etc.)
- ✅ **Mock Models** (for development and testing)

## 🔄 Model Context Protocol (MCP)

nzrRest implements the Model Context Protocol for stateful AI interactions:

```python
# MCP-compliant endpoint
@router.post("/mcp/{model_name}/predict")
async def mcp_predict(request, model_name: str):
    # Automatic context management
    mcp_request = MCPRequest(**(await request.json()))
    
    # Retrieve conversation context
    context = await get_context(mcp_request.context_id)
    
    # Make prediction with context
    model = request.app.ai_registry.get_model(model_name)
    result = await model.predict(mcp_request.payload, context)
    
    # Return MCP-compliant response
    return MCPResponse(
        request_id=mcp_request.request_id,
        context_id=mcp_request.context_id,
        result=result
    )
```

## 🎨 Powerful Serializers

nzrRest provides robust data validation:

```python
from nzrrest.serializers import BaseSerializer, CharField, IntegerField

class ChatRequestSerializer(BaseSerializer):
    message = CharField(max_length=1000)
    user_id = CharField(required=False)
    temperature = FloatField(min_value=0.0, max_value=2.0, default=0.7)
    
    def validate(self, data):
        # Custom validation logic
        return data

# Use in endpoints
@router.post("/chat")
async def chat(request):
    data = await request.json()
    serializer = ChatRequestSerializer(data=data)
    
    if serializer.is_valid():
        validated_data = serializer.validated_data
        # Process with confidence...
    else:
        return JSONResponse(serializer.errors, status_code=422)
```

## 🗄️ Database Integration

Built-in async database support with SQLAlchemy:

```python
from nzrrest.db import Base
from sqlalchemy import Column, Integer, String, DateTime

class ConversationHistory(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), index=True)
    message = Column(Text)
    response = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# Use in endpoints
@router.post("/chat")
async def chat(request):
    async with request.app.get_db_session() as session:
        # Save conversation
        conversation = ConversationHistory(
            user_id=user_id,
            message=message,
            response=response
        )
        session.add(conversation)
        await session.commit()
```

## 🛡️ Production Features

### Rate Limiting
```python
from nzrrest.middleware import RateLimitMiddleware

app.add_middleware(
    RateLimitMiddleware,
    calls_per_minute=60,
    calls_per_hour=1000
)
```

### Authentication
```python
from nzrrest.middleware import AuthenticationMiddleware

app.add_middleware(
    AuthenticationMiddleware,
    secret_key="your-secret-key"
)
```

### CORS for n8n
```python
from starlette.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.n8n.cloud"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

## 🔧 CLI Tools

nzrRest includes powerful CLI tools for development:

```bash
# Create new project
nzrrest new my-project --template mcp-server

# Run development server  
nzrrest run --reload --port 8000

# Database migrations
nzrrest migrate -m "Add user table"
nzrrest migrate --upgrade

# Model management
nzrrest models --list
nzrrest models --add openai_gpt4 --type openai

# Project info
nzrrest info
```

## 🌐 n8n Integration

Perfect for n8n workflows with built-in MCP support:

```json
{
  "nodes": [{
    "name": "AI Chat",
    "type": "n8n-nodes-base.httpRequest",
    "parameters": {
      "url": "http://your-api.com/api/v1/mcp/gpt4/predict",
      "method": "POST",
      "body": {
        "context_id": "{{ $json.session_id }}",
        "payload": {
          "message": "{{ $json.user_input }}"
        }
      }
    }
  }]
}
```

## 📊 Monitoring & Observability

Built-in monitoring capabilities:

```python
# Health checks
GET /health
GET /api/v1/models/{name}/health

# Metrics
GET /metrics
GET /api/v1/stats

# Usage analytics
GET /api/v1/usage/models
GET /api/v1/conversations/{context_id}
```

## 🐳 Docker Deployment

Production-ready containers:

```dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t my-ai-api .
docker run -p 8000:8000 my-ai-api

# Or use docker-compose
docker-compose up -d
```

## 📚 Examples

Check out our comprehensive examples:

- [**Basic API**](examples/basic_api.py) - Simple AI API with chat functionality
- [**Advanced Chatbot**](examples/ai_chatbot.py) - Full-featured chatbot with personality
- [**n8n Integration**](examples/n8n_integration/) - Complete n8n workflow examples
- [**Custom Models**](examples/custom_models/) - Implementing your own AI models

## 📖 Documentation

- [**Quick Start Guide**](https://nzrrest.readthedocs.io/quickstart/)
- [**API Reference**](https://nzrrest.readthedocs.io/api/)
- [**AI Model Integration**](https://nzrrest.readthedocs.io/models/)
- [**MCP Specification**](https://nzrrest.readthedocs.io/mcp/)
- [**Deployment Guide**](https://nzrrest.readthedocs.io/deployment/)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

```bash
# Development setup
git clone https://github.com/nzrrest/nzrrest.git
cd nzrrest
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
black .
isort .
flake8
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built on the excellent FastAPI and Starlette foundations  
- Designed for seamless n8n integration
- Community-driven development

## 🔗 Links

- **Homepage**: [https://nzrrest.dev](https://nzrrest.dev)
- **Documentation**: [https://nzrrest.readthedocs.io](https://nzrrest.readthedocs.io)
- **PyPI**: [https://pypi.org/project/nzrrest/](https://pypi.org/project/nzrrest/)
- **GitHub**: [https://github.com/nzrrest/nzrrest](https://github.com/nzrrest/nzrrest)
- **Discord**: [https://discord.gg/nzrrest](https://discord.gg/nzrrest)

---

<div align="center">

**Built with ❤️ for the AI community**

*nzrRest Framework - Making AI APIs Simple and Powerful*

</div>