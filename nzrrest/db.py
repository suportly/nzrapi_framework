"""
Database integration with SQLAlchemy async for nzrRest framework
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Type

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    AsyncSessionTransaction,
    AsyncTransaction,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, declarative_base, relationship
from sqlalchemy.pool import StaticPool

from .exceptions import NzrRestException


# Base class for SQLAlchemy models
class Base(DeclarativeBase):
    """Base class for all database models"""

    pass


class DatabaseManager:
    """Manages database connections and sessions for nzrRest"""

    def __init__(
        self,
        database_url: str,
        echo: bool = False,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
    ):
        """Initialize database manager

        Args:
            database_url: Database connection URL
            echo: Whether to echo SQL statements
            pool_size: Size of the connection pool
            max_overflow: Maximum overflow connections
            pool_timeout: Connection timeout in seconds
            pool_recycle: Connection recycle time in seconds
        """
        self.database_url = database_url
        self.echo = echo

        # Engine configuration
        self.engine_kwargs: Dict[str, Any] = {
            "echo": echo,
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_timeout": pool_timeout,
            "pool_recycle": pool_recycle,
        }

        # Handle SQLite special case
        if database_url.startswith("sqlite"):
            self.engine_kwargs.update({"poolclass": StaticPool, "connect_args": {"check_same_thread": False}})

        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self._metadata = MetaData()

    async def connect(self) -> None:
        """Connect to the database"""
        try:
            self.engine = create_async_engine(self.database_url, **self.engine_kwargs)
            self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

            # Test the connection
            async with self.engine.begin() as conn:
                await conn.run_sync(lambda sync_conn: None)

        except Exception as e:
            raise NzrRestException(f"Failed to connect to database: {e}")

    async def disconnect(self) -> None:
        """Disconnect from the database"""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session

        Yields:
            AsyncSession: Database session

        Raises:
            RuntimeError: If database is not connected
        """
        if not self.session_factory:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def create_tables(self, base: Type[DeclarativeBase] = Base) -> None:
        """Create all tables

        Args:
            base: Base class containing table definitions
        """
        if not self.engine:
            raise RuntimeError("Database not connected")

        async with self.engine.begin() as conn:
            await conn.run_sync(base.metadata.create_all)

    async def drop_tables(self, base: Type[DeclarativeBase] = Base) -> None:
        """Drop all tables

        Args:
            base: Base class containing table definitions
        """
        if not self.engine:
            raise RuntimeError("Database not connected")

        async with self.engine.begin() as conn:
            await conn.run_sync(base.metadata.drop_all)

    async def execute_raw_sql(self, sql: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Execute raw SQL

        Args:
            sql: SQL statement
            parameters: Optional parameters for the SQL

        Returns:
            Result of the SQL execution
        """
        if not self.engine:
            raise RuntimeError("Database not connected")

        async with self.engine.begin() as conn:
            result = await conn.execute(text(sql), parameters or {})
            return result

    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check

        Returns:
            Dictionary with health status
        """
        if not self.engine:
            return {"status": "disconnected", "error": "Database not connected"}

        try:
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            return {
                "status": "healthy",
                "database_url": (self.database_url.split("@")[-1] if "@" in self.database_url else self.database_url),
                "pool_size": self.engine.pool.status().get("checkedin"),  # type: ignore[attr-defined]
                "checked_out": self.engine.pool.status().get("checkedout"),  # type: ignore[attr-defined]
                "overflow": self.engine.pool.status().get("overflow"),  # type: ignore[attr-defined]
            }

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


class Repository:
    """Base repository class for database operations"""

    def __init__(self, session: AsyncSession, model_class: Type[Base]):
        """Initialize repository

        Args:
            session: Database session
            model_class: SQLAlchemy model class
        """
        self.session = session
        self.model_class = model_class

    async def create(self, **kwargs) -> Base:
        """Create a new record

        Args:
            **kwargs: Field values for the new record

        Returns:
            Created model instance
        """
        instance = self.model_class(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def get_by_id(self, id: Any) -> Optional[Base]:
        """Get record by ID

        Args:
            id: Record ID

        Returns:
            Model instance or None if not found
        """
        return await self.session.get(self.model_class, id)

    async def get_by_field(self, field: str, value: Any) -> Optional[Base]:
        """Get record by field value

        Args:
            field: Field name
            value: Field value

        Returns:
            Model instance or None if not found
        """
        from sqlalchemy import select

        stmt = select(self.model_class).where(getattr(self.model_class, field) == value)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, limit: Optional[int] = None, offset: int = 0) -> list[Base]:
        """List all records

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of model instances
        """
        from sqlalchemy import select

        stmt = select(self.model_class).offset(offset)
        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, instance: Base, **kwargs) -> Base:
        """Update a record

        Args:
            instance: Model instance to update
            **kwargs: Field values to update

        Returns:
            Updated model instance
        """
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: Base) -> None:
        """Delete a record

        Args:
            instance: Model instance to delete
        """
        await self.session.delete(instance)
        await self.session.flush()

    async def count(self) -> int:
        """Count total records

        Returns:
            Total number of records
        """
        from sqlalchemy import func, select

        stmt = select(func.count()).select_from(self.model_class)
        result = await self.session.execute(stmt)
        return result.scalar()


class TransactionManager:
    """Manages database transactions"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._savepoints: List[Tuple[str, AsyncSessionTransaction]] = []

    async def begin_savepoint(self, name: Optional[str] = None) -> str:
        """Begin a savepoint

        Args:
            name: Optional savepoint name

        Returns:
            Savepoint name
        """
        if not name:
            name = f"sp_{len(self._savepoints)}"

        savepoint = await self.session.begin_nested()
        self._savepoints.append((name, savepoint))
        return name

    async def rollback_to_savepoint(self, name: str) -> None:
        """Rollback to a specific savepoint

        Args:
            name: Savepoint name
        """
        for i, (sp_name, savepoint) in enumerate(reversed(self._savepoints)):
            if sp_name == name:
                await savepoint.rollback()
                # Remove this savepoint and all nested ones
                self._savepoints = self._savepoints[: -(i + 1)]
                return

        raise ValueError(f"Savepoint '{name}' not found")

    async def commit_savepoint(self, name: str) -> None:
        """Commit a specific savepoint

        Args:
            name: Savepoint name
        """
        for i, (sp_name, savepoint) in enumerate(reversed(self._savepoints)):
            if sp_name == name:
                await savepoint.commit()
                # Remove this savepoint
                del self._savepoints[-(i + 1)]
                return

        raise ValueError(f"Savepoint '{name}' not found")


class DatabaseMiddleware:
    """Middleware to provide database session to requests"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def __call__(self, request, call_next):
        """Middleware implementation"""
        # Add database session to request
        async with self.db_manager.get_session() as session:
            request.state.db_session = session
            response = await call_next(request)
            return response


# Utility functions
def get_database_url_from_env() -> str:
    """Get database URL from environment variables"""
    import os

    # Try different environment variable names
    url = (
        os.getenv("DATABASE_URL")
        or os.getenv("DB_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URL")
        or "sqlite+aiosqlite:///./app.db"  # Default to SQLite
    )

    return url


async def init_database(database_url: str, create_tables: bool = True) -> DatabaseManager:
    """Initialize database with default configuration

    Args:
        database_url: Database connection URL
        create_tables: Whether to create tables

    Returns:
        Configured DatabaseManager instance
    """
    db_manager = DatabaseManager(database_url)
    await db_manager.connect()

    if create_tables:
        await db_manager.create_tables()

    return db_manager


# Example models for reference


class ConversationHistory(Base):
    """Example model for storing AI conversation history"""

    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, index=True)
    context_id = Column(String(255), index=True, nullable=False)
    model_name = Column(String(100), nullable=False)
    input_payload = Column(Text, nullable=False)
    output_result = Column(Text, nullable=False)
    context_data = Column(Text)  # JSON serialized context
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    execution_time = Column(Integer)  # milliseconds
    tokens_used = Column(Integer)

    @classmethod
    async def get_by_context_id(cls, session: AsyncSession, context_id: str):
        """Get conversation by context ID"""
        from sqlalchemy import select

        stmt = select(cls).where(cls.context_id == context_id).order_by(cls.created_at.desc())
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


class APIKey(Base):
    """Example model for API key management"""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key_hash = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime)
    usage_count = Column(Integer, default=0, nullable=False)
    rate_limit = Column(Integer, default=1000)  # requests per hour
