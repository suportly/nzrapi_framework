"""
Configuration settings for {{ project_name }}
"""

import os
from typing import List


class Settings:
    """Application settings"""
    
    # Basic settings
    PROJECT_NAME: str = "{{ project_name }}"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Database settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite+aiosqlite:///./{{ project_name }}.db"
    )
    
    # CORS settings
    ENABLE_CORS: bool = {{ include_cors | lower }}
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://app.n8n.cloud",
        "https://*.n8n.cloud"
    ]
    
    # Rate limiting
    ENABLE_RATE_LIMITING: bool = True
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_PER_HOUR: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
    
    # Authentication (if enabled)
    {% if include_auth %}
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    {% endif %}
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


# Create settings instance
settings = Settings()


# AI Models Configuration
AI_MODELS_CONFIG = {
    "models": [
        {
            "name": "{{ default_model }}",
            "type": "{{ default_model }}",
            "auto_load": True,
            "config": {
                {% if default_model == "mock" %}
                "mock_responses": {
                    "hello": "Hello! I'm a mock AI model.",
                    "test": "This is a test response from the mock model."
                },
                "simulation_delay": 0.1
                {% elif default_model == "openai" %}
                "api_key": os.getenv("OPENAI_API_KEY"),
                "model_id": "gpt-3.5-turbo",
                "max_tokens": 1000,
                "temperature": 0.7
                {% elif default_model == "anthropic" %}
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "model_id": "claude-3-sonnet",
                "max_tokens": 1000
                {% endif %}
            }
        }
    ]
}

# Example of adding more models
# AI_MODELS_CONFIG["models"].append({
#     "name": "another_model",
#     "type": "openai",
#     "auto_load": False,
#     "config": {
#         "api_key": os.getenv("OPENAI_API_KEY"),
#         "model_id": "gpt-4",
#         "max_tokens": 2000
#     }
# })