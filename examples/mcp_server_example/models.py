"""
Database models for mcp_server_example
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

Base = declarative_base()


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
                func.date(cls.date).label("date"),
                func.sum(cls.requests_count).label("requests"),
                func.sum(cls.total_tokens).label("tokens"),
                func.avg(cls.total_execution_time).label("avg_time"),
                func.sum(cls.error_count).label("errors"),
            )
            .where(cls.model_name == model_name)
            .where(cls.date >= cutoff_date)
            .group_by(func.date(cls.date))
            .order_by(func.date(cls.date))
        )

        result = await session.execute(stmt)
        return result.all()
