"""
Configuration management for dependency injection example
"""

import os
from typing import List

from pydantic import BaseModel

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings


class DatabaseConfig(BaseModel):
    """Database configuration"""

    url: str = "sqlite:///./demo.db"
    echo: bool = False
    pool_size: int = 10


class SecurityConfig(BaseModel):
    """Security configuration"""

    secret_key: str
    algorithm: str = "HS256"
    token_expire_minutes: int = 30
    password_min_length: int = 6


class AppConfig(BaseModel):
    """Application configuration"""

    name: str = "Clean Dependency Injection Demo"
    version: str = "1.0.0"
    max_users: int = 1000
    cors_origins: List[str] = ["http://localhost:3000"]


class Settings(BaseSettings):
    """Main settings class"""

    debug: bool = True

    database: DatabaseConfig = DatabaseConfig()
    security: SecurityConfig
    app: AppConfig = AppConfig()

    def __init__(self, **kwargs):
        # Generate secret key if not provided
        if "security" not in kwargs:
            from nzrapi.security import generate_secret_key

            kwargs["security"] = SecurityConfig(secret_key=generate_secret_key())
        super().__init__(**kwargs)

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"
        extra = "ignore"  # Ignore extra environment variables


# Global settings instance
settings = Settings()
