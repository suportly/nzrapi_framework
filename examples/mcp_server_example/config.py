"""
Configuration settings for mcp_server_example
"""

import logging
import os
from typing import List


class Settings:
    """Application settings"""

    # Basic settings
    PROJECT_NAME: str = "mcp_server_example"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./mcp_server_example.db")

    # CORS settings
    ENABLE_CORS: bool = True
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://app.n8n.cloud",
        "https://*.n8n.cloud",
    ]

    # Rate limiting
    ENABLE_RATE_LIMITING: bool = True
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_PER_HOUR: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))

    # Authentication (if enabled)

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


# Create settings instance
settings = Settings()


# AI Models Configuration
AI_MODELS_CONFIG = {
    "models": [
        {
            "name": "openai_chat",
            "type": "openai",
            "auto_load": True,
            "config": {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "model_id": "gpt-4o-mini",
            },
        }
    ]
}
