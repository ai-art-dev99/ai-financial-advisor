"""
Conversation Manager
Stores per-user chat history in Redis with TTL.
Each message: {"role": "user"|"assistant", "content": "..."}
"""
import json
import redis.asyncio as aioredis
from typing import List
from config import settings


class ConversationManager:
    def __init__(self):
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = await aioredis.from_url(
                settings.redis_url, encoding="utf-8", decode_responses=True
            )
        return self._redis

    def _key(self, session_id: str) -> str:
        return f"chat:session:{session_id}"

    async def get_history(self, session_id: str) -> List[dict]:
        r = await self._get_redis()
        raw = await r.get(self._key(session_id))
        if not raw:
            return []
        return json.loads(raw)

    async def append_messages(self, session_id: str, messages: List[dict]) -> None:
        r = await self._get_redis()
        key = self._key(session_id)
        history = await self.get_history(session_id)
        history.extend(messages)

        # Keep only last N messages (rolling window)
        if len(history) > settings.max_history_messages:
            history = history[-settings.max_history_messages:]

        await r.set(key, json.dumps(history), ex=settings.session_ttl_seconds)

    async def clear_session(self, session_id: str) -> None:
        r = await self._get_redis()
        await r.delete(self._key(session_id))

    async def get_all_sessions(self, user_id: str) -> List[str]:
        r = await self._get_redis()
        keys = await r.keys(f"chat:session:{user_id}:*")
        return [k.split(":")[-1] for k in keys]


conversation_manager = ConversationManager()