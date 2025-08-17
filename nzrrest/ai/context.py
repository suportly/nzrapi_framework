"""
Context management for AI conversations and stateful interactions
"""

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .protocol import ContextData


@dataclass
class ContextConfig:
    """Configuration for context management"""

    default_ttl: int = 3600  # 1 hour
    max_contexts: int = 10000
    cleanup_interval: int = 300  # 5 minutes
    persistence_enabled: bool = False
    compression_enabled: bool = True
    max_message_history: int = 100


class ContextManager:
    """Manages conversation contexts and state for AI models"""

    def __init__(self, config: Optional[ContextConfig] = None):
        self.config = config or ContextConfig()
        self.contexts: Dict[str, ContextData] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

        # Statistics
        self.stats = {
            "contexts_created": 0,
            "contexts_accessed": 0,
            "contexts_expired": 0,
            "contexts_cleaned": 0,
        }

    async def start(self):
        """Start the context manager and cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_worker())

    async def stop(self):
        """Stop the context manager and cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def create_context(
        self,
        context_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> ContextData:
        """Create a new context

        Args:
            context_id: Unique context identifier
            metadata: Optional metadata for the context
            ttl: Time to live in seconds (uses default if not specified)

        Returns:
            Created context data

        Raises:
            ValueError: If context already exists
        """
        async with self._lock:
            if context_id in self.contexts:
                raise ValueError(f"Context '{context_id}' already exists")

            # Check if we're at capacity
            if len(self.contexts) >= self.config.max_contexts:
                await self._cleanup_expired_contexts()

                # If still at capacity, remove oldest context
                if len(self.contexts) >= self.config.max_contexts:
                    oldest_id = min(self.contexts.keys(), key=lambda k: self.contexts[k].created_at)
                    del self.contexts[oldest_id]
                    self.stats["contexts_cleaned"] += 1

            context = ContextData(
                context_id=context_id,
                metadata=metadata or {},
                ttl=ttl or self.config.default_ttl,
            )

            self.contexts[context_id] = context
            self.stats["contexts_created"] += 1

            return context

    async def get_context(self, context_id: str) -> Optional[ContextData]:
        """Get a context by ID

        Args:
            context_id: Context identifier

        Returns:
            Context data or None if not found or expired
        """
        async with self._lock:
            if context_id not in self.contexts:
                return None

            context = self.contexts[context_id]

            # Check if expired
            if context.is_expired():
                del self.contexts[context_id]
                self.stats["contexts_expired"] += 1
                return None

            self.stats["contexts_accessed"] += 1
            return context

    async def update_context(self, context_id: str, **updates) -> Optional[ContextData]:
        """Update context data

        Args:
            context_id: Context identifier
            **updates: Fields to update

        Returns:
            Updated context or None if not found
        """
        async with self._lock:
            context = self.contexts.get(context_id)
            if not context or context.is_expired():
                return None

            # Update fields
            if "metadata" in updates:
                context.metadata.update(updates["metadata"])

            if "state" in updates:
                context.state.update(updates["state"])

            if "ttl" in updates:
                context.ttl = updates["ttl"]

            context.updated_at = datetime.utcnow()
            return context

    async def add_message(
        self,
        context_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add a message to a context

        Args:
            context_id: Context identifier
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional message metadata

        Returns:
            True if message was added, False if context not found
        """
        async with self._lock:
            context = self.contexts.get(context_id)
            if not context or context.is_expired():
                return False

            context.add_message(role, content, metadata)

            # Trim message history if too long
            if len(context.messages) > self.config.max_message_history:
                # Keep first message (often system prompt) and recent messages
                first_message = context.messages[0] if context.messages else None
                recent_messages = context.messages[-(self.config.max_message_history - 1) :]

                context.messages = [first_message] + recent_messages if first_message else recent_messages

            return True

    async def update_state(self, context_id: str, key: str, value: Any) -> bool:
        """Update a state value in a context

        Args:
            context_id: Context identifier
            key: State key
            value: State value

        Returns:
            True if state was updated, False if context not found
        """
        async with self._lock:
            context = self.contexts.get(context_id)
            if not context or context.is_expired():
                return False

            context.update_state(key, value)
            return True

    async def delete_context(self, context_id: str) -> bool:
        """Delete a context

        Args:
            context_id: Context identifier

        Returns:
            True if context was deleted, False if not found
        """
        async with self._lock:
            if context_id in self.contexts:
                del self.contexts[context_id]
                return True
            return False

    async def list_contexts(self, filter_expired: bool = True) -> List[Dict[str, Any]]:
        """List all contexts

        Args:
            filter_expired: Whether to exclude expired contexts

        Returns:
            List of context summaries
        """
        async with self._lock:
            contexts = []

            for context_id, context in list(self.contexts.items()):
                if filter_expired and context.is_expired():
                    del self.contexts[context_id]
                    self.stats["contexts_expired"] += 1
                    continue

                contexts.append(
                    {
                        "context_id": context_id,
                        "created_at": context.created_at.isoformat(),
                        "updated_at": context.updated_at.isoformat(),
                        "message_count": len(context.messages),
                        "metadata": context.metadata,
                        "ttl": context.ttl,
                        "expires_at": (
                            (context.updated_at + timedelta(seconds=context.ttl)).isoformat() if context.ttl else None
                        ),
                    }
                )

            return contexts

    async def cleanup_expired(self) -> int:
        """Clean up expired contexts

        Returns:
            Number of contexts cleaned up
        """
        async with self._lock:
            return await self._cleanup_expired_contexts()

    async def _cleanup_expired_contexts(self) -> int:
        """Internal method to clean up expired contexts"""
        expired_count = 0

        for context_id in list(self.contexts.keys()):
            context = self.contexts[context_id]
            if context.is_expired():
                del self.contexts[context_id]
                expired_count += 1
                self.stats["contexts_expired"] += 1

        return expired_count

    async def _cleanup_worker(self):
        """Background worker for periodic cleanup"""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
            except asyncio.CancelledError:
                break

            try:
                cleaned = await self.cleanup_expired()
                if cleaned > 0:
                    # In a real app, you'd use a logger
                    # print(f"Cleaned up {cleaned} expired contexts")
                    pass
            except Exception as e:
                # In a real app, you'd use a logger
                # print(f"Error in context cleanup worker: {e}")
                pass

    def get_stats(self) -> Dict[str, Any]:
        """Get context manager statistics

        Returns:
            Dictionary with statistics
        """
        return {
            **self.stats,
            "active_contexts": len(self.contexts),
            "max_contexts": self.config.max_contexts,
            "default_ttl": self.config.default_ttl,
            "cleanup_interval": self.config.cleanup_interval,
        }

    async def export_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """Export context data for backup or transfer

        Args:
            context_id: Context identifier

        Returns:
            Serializable context data or None if not found
        """
        context = await self.get_context(context_id)
        if not context:
            return None

        return {
            "context_id": context.context_id,
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat(),
            "metadata": context.metadata,
            "messages": context.messages,
            "state": context.state,
            "ttl": context.ttl,
        }

    async def import_context(self, data: Dict[str, Any]) -> ContextData:
        """Import context data from backup or transfer

        Args:
            data: Serialized context data

        Returns:
            Imported context
        """
        context_id = data["context_id"]

        context = ContextData(
            context_id=context_id,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data["metadata"],
            messages=data["messages"],
            state=data["state"],
            ttl=data["ttl"],
        )

        async with self._lock:
            self.contexts[context_id] = context

        return context

    async def clear_all(self) -> int:
        """Clear all contexts

        Returns:
            Number of contexts cleared
        """
        async with self._lock:
            count = len(self.contexts)
            self.contexts.clear()
            self.stats["contexts_cleaned"] += count
            return count
