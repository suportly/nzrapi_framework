"""
Database models for {{ project_name }}
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession

from nzrrest.db import Base


class ConversationHistory(Base):
    """Model for storing AI conversation history"""
    __tablename__ = "conversation_history"
    
    id = Column(Integer, primary_key=True, index=True)
    context_id = Column(String(255), index=True, nullable=False)
    model_name = Column(String(100), nullable=False)
    input_payload = Column(Text, nullable=False)  # JSON serialized
    output_result = Column(Text, nullable=False)  # JSON serialized
    context_data = Column(Text)  # JSON serialized context
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    execution_time = Column(Float)  # seconds
    tokens_used = Column(Integer)
    success = Column(Boolean, default=True, nullable=False)
    
    @classmethod
    async def get_by_context_id(cls, session: AsyncSession, context_id: str):
        """Get conversation history by context ID"""
        from sqlalchemy import select
        
        stmt = select(cls).where(cls.context_id == context_id).order_by(cls.created_at.desc())
        result = await session.execute(stmt)
        return result.scalars().all()
    
    @classmethod
    async def get_latest_by_context(cls, session: AsyncSession, context_id: str):
        """Get latest conversation by context ID"""
        from sqlalchemy import select
        
        stmt = select(cls).where(cls.context_id == context_id).order_by(cls.created_at.desc()).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


class ModelUsageStats(Base):
    """Model for tracking AI model usage statistics"""
    __tablename__ = "model_usage_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False, index=True)
    date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    requests_count = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    total_execution_time = Column(Float, default=0.0, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)
    
    @classmethod
    async def get_stats_by_model(cls, session: AsyncSession, model_name: str, days: int = 7):
        """Get usage statistics for a model over the last N days"""
        from datetime import timedelta

        from sqlalchemy import func, select
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(
                func.date(cls.date).label('date'),
                func.sum(cls.requests_count).label('requests'),
                func.sum(cls.total_tokens).label('tokens'),
                func.avg(cls.total_execution_time).label('avg_time'),
                func.sum(cls.error_count).label('errors')
            )
            .where(cls.model_name == model_name)
            .where(cls.date >= cutoff_date)
            .group_by(func.date(cls.date))
            .order_by(func.date(cls.date))
        )
        
        result = await session.execute(stmt)
        return result.all()


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