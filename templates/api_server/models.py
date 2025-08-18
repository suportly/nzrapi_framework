"""
Database models for {{ project_name }}
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession

from nzrapi.db import Base

# Add your custom models here
#
# Example:
#
# class Item(Base):
#     __tablename__ = "items"
#
#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String(100), nullable=False)
#     description = Column(Text)
#     price = Column(Float, nullable=False)
#     is_available = Column(Boolean, default=True)
{% if include_auth %}
class APIKey(Base):
    """Model for API key management"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    key_hash = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime)
    usage_count = Column(Integer, default=0, nullable=False)
    rate_limit = Column(Integer, default=1000)  # requests per hour
    
    @classmethod
    async def get_by_key_hash(cls, session: AsyncSession, key_hash: str):
        """Get API key by hash"""
        from sqlalchemy import select
        
        stmt = select(cls).where(cls.key_hash == key_hash, cls.is_active == True)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_usage(self, session: AsyncSession):
        """Update usage statistics"""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()
        await session.commit()


class User(Base):
    """Model for user management"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime)
    
    @classmethod
    async def get_by_username(cls, session: AsyncSession, username: str):
        """Get user by username"""
        from sqlalchemy import select
        
        stmt = select(cls).where(cls.username == username, cls.is_active == True)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_by_email(cls, session: AsyncSession, email: str):
        """Get user by email"""
        from sqlalchemy import select
        
        stmt = select(cls).where(cls.email == email, cls.is_active == True)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
{% endif %}