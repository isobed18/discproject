import json
import logging
from typing import Any, Dict, List, Optional
import redis.asyncio as redis
from core.config import settings

logger = logging.getLogger(__name__)

class RedisAuditIndexer:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        try:
            self.redis = redis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("Redis Audit Indexer connected.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis for indexing: {e}")
            self.redis = None

    async def close(self):
        if self.redis:
            await self.redis.close()

    async def index_event(self, event: Dict[str, Any]):
        """
        Stores the event in Redis and updates search indices.
        Indexes:
        - audit:msg:{id} (Hash) -> Full Data
        - audit:idx:actor:{actor} (Set) -> {id}
        - audit:idx:action:{action} (Set) -> {id}
        - audit:timeline (Sorted Set) -> {id} (score=timestamp)
        """
        if not self.redis:
            return

        try:
            event_id = event["event_id"]
            timestamp_str = event["timestamp"]
            # Convert ISO to float timestamp for ZADD score
            # Simple approach: Use direct float if available, or just ASCII sort if ISO8601
            # Ideally ZADD needs a Score (float). 
            # We can use datetime.fromisoformat(timestamp_str).timestamp()
            from datetime import datetime
            score = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).timestamp()

            pipeline = self.redis.pipeline()
            
            # 1. Store full event
            pipeline.hset(f"audit:msg:{event_id}", mapping={
                "json": json.dumps(event)
            })
            pipeline.expire(f"audit:msg:{event_id}", 2592000) # 30 days retention

            # 2. Index by Actor
            if actor := event.get("actor"):
                pipeline.sadd(f"audit:idx:actor:{actor}", event_id)
                pipeline.expire(f"audit:idx:actor:{actor}", 2592000)

            # 3. Index by Action
            if action := event.get("action"):
                pipeline.sadd(f"audit:idx:action:{action}", event_id)
                pipeline.expire(f"audit:idx:action:{action}", 2592000)

            # 4. Timeline (Sorted Set)
            pipeline.zadd("audit:timeline", {event_id: score})
            # Trim timeline to Keep last 10,000 events to prevent bloating in MVP
            pipeline.zremrangebyrank("audit:timeline", 0, -10001)

            await pipeline.execute()
            
        except Exception as e:
            logger.error(f"Failed to index audit event in Redis: {e}")

    async def search(
        self, 
        actor: Optional[str] = None, 
        action: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Simple intersection search.
        If no filters, return latest from timeline.
        """
        if not self.redis:
            return []

        try:
            candidate_ids = set()
            is_filtered = False

            # If filtering by multiple criteria, we should INTERSECT
            # For MVP, let's start with individual or fallback.
            
            keys_to_intersect = []
            if actor:
                keys_to_intersect.append(f"audit:idx:actor:{actor}")
            if action:
                keys_to_intersect.append(f"audit:idx:action:{action}")

            if keys_to_intersect:
                # Get common IDs
                candidate_ids = await self.redis.sinter(keys_to_intersect)
                is_filtered = True
            
            final_ids = []
            if is_filtered:
                if not candidate_ids:
                    return []
                final_ids = list(candidate_ids)[:limit] # No sorting for set yet
            else:
                # No filters, return latest from timeline
                final_ids = await self.redis.zrevrange("audit:timeline", 0, limit - 1)

            results = []
            for eid in final_ids:
                data = await self.redis.hget(f"audit:msg:{eid}", "json")
                if data:
                    results.append(json.loads(data))
            
            return results

        except Exception as e:
            logger.error(f"Audit search failed: {e}")
            return []

# Singleton
audit_indexer = RedisAuditIndexer()
