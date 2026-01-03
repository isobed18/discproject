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
        except Exception:
            self.redis = None

    async def close(self):
        if self.redis:
            await self.redis.close()

    async def index_event(self, event: Dict[str, Any]):
        if not self.redis: return

        try:
            event_id = event["event_id"]
            timestamp_str = event["timestamp"]
            
            from datetime import datetime
            try:
                score = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).timestamp()
            except:
                import time
                score = time.time()

            pipeline = self.redis.pipeline()
            
            # 1. Veriyi Kaydet
            pipeline.hset(f"audit:msg:{event_id}", mapping={"json": json.dumps(event)})
            pipeline.expire(f"audit:msg:{event_id}", 2592000)

            # 2. Actor İndeksi
            if actor := event.get("actor"):
                pipeline.sadd(f"audit:idx:actor:{actor}", event_id)
                pipeline.expire(f"audit:idx:actor:{actor}", 2592000)

            # 3. Action İndeksi
            if action := event.get("action"):
                pipeline.sadd(f"audit:idx:action:{action}", event_id)
                pipeline.expire(f"audit:idx:action:{action}", 2592000)

            # --- 4. YENİ: Correlation ID İndeksi (Sorunu Çözen Yer) ---
            if cid := event.get("correlation_id"):
                pipeline.sadd(f"audit:idx:correlation:{cid}", event_id)
                pipeline.expire(f"audit:idx:correlation:{cid}", 2592000)

            # 5. Timeline
            pipeline.zadd("audit:timeline", {event_id: score})
            pipeline.zremrangebyrank("audit:timeline", 0, -10001)

            await pipeline.execute()
        except Exception as e:
            logger.error(f"Index error: {e}")

    # --- Search Fonksiyonunu da İndekse Göre Güncelleyelim ---
    async def search(self, actor=None, action=None, correlation_id=None, limit=50):
        if not self.redis: return []

        try:
            candidate_ids = set()
            is_filtered = False
            keys = []

            if actor: keys.append(f"audit:idx:actor:{actor}")
            if action: keys.append(f"audit:idx:action:{action}")
            # Eğer correlation_id aranıyorsa direkt indeksten bul!
            if correlation_id: keys.append(f"audit:idx:correlation:{correlation_id}")

            if keys:
                candidate_ids = await self.redis.sinter(keys)
                is_filtered = True
            
            final_ids = []
            if is_filtered:
                if not candidate_ids: return []
                final_ids = list(candidate_ids)[:limit]
            else:
                final_ids = await self.redis.zrevrange("audit:timeline", 0, limit - 1)

            results = []
            for eid in final_ids:
                data = await self.redis.hget(f"audit:msg:{eid}", "json")
                if data:
                    try:
                        obj = json.loads(data)
                        obj["raw"] = data # Raw görünümü için
                        results.append(obj)
                    except: pass
            return results
        except Exception:
            return []

audit_indexer = RedisAuditIndexer()