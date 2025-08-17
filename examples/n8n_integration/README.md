# nzrRest + n8n Integration Example

This directory contains examples of how to integrate nzrRest AI APIs with n8n workflows.

## Overview

nzrRest is designed to work seamlessly with n8n, providing:

- **Model Context Protocol (MCP)** compliance for stateful AI interactions
- **Structured API responses** that work well with n8n's data processing
- **Error handling** designed for workflow logic
- **Context management** for maintaining conversation state across workflow runs

## Example Workflows

### 1. Basic AI Chat Workflow

```json
{
  "meta": {
    "instanceId": "your-instance-id"
  },
  "nodes": [
    {
      "parameters": {
        "url": "http://your-nzrrest-api.com/api/v1/mcp/advanced_chat/predict",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            {
              "name": "Content-Type",
              "value": "application/json"
            }
          ]
        },
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "context_id",
              "value": "={{ $('Trigger').first().json.session_id }}"
            },
            {
              "name": "payload",
              "value": {
                "message": "={{ $('Trigger').first().json.user_message }}",
                "session_id": "={{ $('Trigger').first().json.session_id }}"
              }
            },
            {
              "name": "metadata",
              "value": {
                "user_id": "={{ $('Trigger').first().json.user_id }}",
                "timestamp": "={{ new Date().toISOString() }}"
              }
            }
          ]
        },
        "options": {}
      },
      "id": "ai-chat-request",
      "name": "AI Chat Request",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.1,
      "position": [640, 300]
    }
  ],
  "connections": {},
  "active": false,
  "settings": {
    "executionOrder": "v1"
  }
}
```

### 2. Customer Support Workflow

A more complex workflow that:
1. Receives customer inquiry
2. Analyzes sentiment 
3. Routes to appropriate AI personality
4. Maintains conversation context
5. Escalates to human if needed

```json
{
  "nodes": [
    {
      "parameters": {
        "url": "http://your-api.com/api/v1/analyze",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "text",
              "value": "={{ $json.customer_message }}"
            },
            {
              "name": "analysis_type",
              "value": "sentiment"
            }
          ]
        }
      },
      "id": "sentiment-analysis",
      "name": "Analyze Sentiment",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.1,
      "position": [460, 300]
    },
    {
      "parameters": {
        "conditions": {
          "options": {
            "caseSensitive": true,
            "leftValue": "",
            "typeValidation": "strict"
          },
          "conditions": [
            {
              "id": "negative-sentiment",
              "leftValue": "={{ $('Analyze Sentiment').first().json.analysis_results.sentiment.sentiment }}",
              "rightValue": "negative",
              "operator": {
                "type": "string",
                "operation": "equals"
              }
            }
          ]
        },
        "options": {}
      },
      "id": "check-sentiment",
      "name": "Check Sentiment",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [680, 300]
    },
    {
      "parameters": {
        "url": "http://your-api.com/api/v1/mcp/professional_chat/predict",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "context_id",
              "value": "={{ $json.conversation_id }}"
            },
            {
              "name": "payload",
              "value": {
                "message": "={{ $json.customer_message }}",
                "priority": "high",
                "sentiment": "negative"
              }
            }
          ]
        }
      },
      "id": "professional-response",
      "name": "Professional AI Response",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.1,
      "position": [900, 200]
    },
    {
      "parameters": {
        "url": "http://your-api.com/api/v1/mcp/friendly_chat/predict",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "context_id",
              "value": "={{ $json.conversation_id }}"
            },
            {
              "name": "payload",
              "value": {
                "message": "={{ $json.customer_message }}"
              }
            }
          ]
        }
      },
      "id": "friendly-response",
      "name": "Friendly AI Response", 
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.1,
      "position": [900, 400]
    }
  ],
  "connections": {
    "Analyze Sentiment": {
      "main": [
        [
          {
            "node": "Check Sentiment",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Check Sentiment": {
      "main": [
        [
          {
            "node": "Professional AI Response",
            "type": "main",
            "index": 0
          }
        ],
        [
          {
            "node": "Friendly AI Response",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  }
}
```

## API Endpoints for n8n

### Chat with Context
```http
POST /api/v1/mcp/{model_name}/predict
Content-Type: application/json

{
  "context_id": "conversation_123",
  "payload": {
    "message": "Hello, I need help with my order",
    "user_id": "user_456"
  },
  "metadata": {
    "channel": "support",
    "priority": "normal"
  }
}
```

**Response:**
```json
{
  "request_id": "req_789",
  "context_id": "conversation_123", 
  "model_name": "professional_chat",
  "result": {
    "response": "I'd be happy to help you with your order. Could you please provide your order number?",
    "confidence": 0.95,
    "intent": "order_support"
  },
  "execution_time": 0.234,
  "model_info": {
    "personality": "professional",
    "capabilities": "context_aware_chat"
  }
}
```

### Text Analysis
```http
POST /api/v1/analyze
Content-Type: application/json

{
  "text": "I'm really frustrated with this product, it doesn't work at all!",
  "analysis_type": "sentiment"
}
```

**Response:**
```json
{
  "analysis_results": {
    "sentiment": {
      "sentiment": "negative",
      "score": 0.15,
      "confidence": 0.89
    }
  },
  "text_length": 65,
  "analysis_type": "sentiment"
}
```

### Conversation History
```http
GET /api/v1/conversations/{context_id}
```

**Response:**
```json
{
  "context_id": "conversation_123",
  "conversation_count": 4,
  "history": [
    {
      "id": 1,
      "model_name": "professional_chat",
      "input": {"message": "Hello, I need help"},
      "output": {"response": "I'm here to help!"},
      "created_at": "2024-01-01T12:00:00Z",
      "success": true
    }
  ]
}
```

## n8n Node Examples

### HTTP Request Node Configuration

```javascript
// Headers
{
  "Content-Type": "application/json",
  "Authorization": "Bearer {{ $('Credentials').first().json.api_key }}"
}

// Body (JSON)
{
  "context_id": "{{ $('Previous Node').first().json.session_id }}",
  "payload": {
    "message": "{{ $json.user_input }}",
    "metadata": {
      "timestamp": "{{ new Date().toISOString() }}",
      "source": "n8n_workflow"
    }
  }
}
```

### Error Handling in n8n

```javascript
// Error Output Expression
{{
  $('AI Request').first().json.error 
    ? "AI_ERROR: " + $('AI Request').first().json.error
    : "Success"
}}

// Conditional Logic Based on AI Response
{{
  $('AI Request').first().json.result?.intent === 'escalate'
    ? 'human_agent'
    : 'continue_ai'
}}
```

## Best Practices for n8n Integration

### 1. Context Management
- Always pass `context_id` to maintain conversation state
- Use meaningful context IDs (e.g., `support_ticket_12345`)
- Clean up old contexts periodically

### 2. Error Handling
```javascript
// Check for API errors
{{ 
  $('AI Request').item?.json?.error 
    ? {
        "error": true,
        "message": $('AI Request').item.json.error,
        "fallback_response": "I'm sorry, I'm having technical difficulties."
      }
    : {
        "error": false,
        "response": $('AI Request').item.json.result.response
      }
}}
```

### 3. Rate Limiting
- Implement delays between requests if needed
- Use n8n's built-in rate limiting features
- Monitor API usage through nzrRest metrics

### 4. Data Transformation
```javascript
// Transform n8n data for nzrRest API
{
  "context_id": "workflow_{{ $workflow.id }}_{{ $execution.id }}",
  "payload": {
    "message": "{{ $json.customer_message }}",
    "conversation_type": "{{ $json.ticket_type || 'general' }}",
    "user_context": {
      "customer_id": "{{ $json.customer_id }}",
      "account_type": "{{ $json.account_tier }}"
    }
  },
  "metadata": {
    "workflow_id": "{{ $workflow.id }}",
    "execution_id": "{{ $execution.id }}",
    "timestamp": "{{ $now.toISOString() }}"
  }
}
```

## Environment Setup

### 1. nzrRest API Configuration
```python
# config.py
CORS_ORIGINS = [
    "https://app.n8n.cloud",
    "https://*.n8n.cloud", 
    "http://localhost:5678"  # Local n8n
]

RATE_LIMIT_PER_MINUTE = 120  # Allow burst traffic from workflows
RATE_LIMIT_PER_HOUR = 5000
```

### 2. n8n Environment Variables
```bash
# .env for n8n
NZRREST_API_URL=https://your-api-domain.com
NZRREST_API_KEY=your-api-key
```

### 3. Docker Deployment
```yaml
# docker-compose.yml
version: '3.8'
services:
  nzrrest-api:
    build: .
    environment:
      - CORS_ORIGINS=["https://app.n8n.cloud"]
    ports:
      - "8000:8000"
    
  n8n:
    image: n8nio/n8n
    environment:
      - NZRREST_API_URL=http://nzrrest-api:8000
    ports:
      - "5678:5678"
    depends_on:
      - nzrrest-api
```

## Monitoring and Debugging

### Check API Health
```http
GET /health
```

### View Model Status
```http
GET /api/v1/models
```

### Monitor Usage
```http
GET /api/v1/stats
```

### Debug Conversations
```http
GET /api/v1/conversations/{context_id}
```

This integration provides a powerful foundation for building AI-powered automation workflows with n8n and nzrRest!