import asyncio
import json
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional, Tuple


def _iso_now() -> str:
    # Avoid timezone import to keep this module lightweight; ISO string is enough.
    return datetime.utcnow().isoformat() + "Z"


def _safe_str(v: Any) -> str:
    try:
        if isinstance(v, str):
            return v
        return json.dumps(v, ensure_ascii=False, default=str)
    except Exception:
        return str(v)


class AuditEventStore:
    """In-memory ring buffer for audit events.

    We keep a *flattened* envelope so the UI can render it without knowing whether
    the record came from Kafka or direct local writes.
    """

    def __init__(self, maxlen: int = 5000):
        self._events: Deque[Dict[str, Any]] = deque(maxlen=maxlen)
        self._seen_ids: set[str] = set()
        self._lock = asyncio.Lock()
        self._maxlen = maxlen

        # Lightweight health/observability
        self.kafka_connected: bool = False
        self.kafka_last_ingest_at: Optional[str] = None
        self.kafka_last_error: Optional[str] = None
        self.kafka_consumed_total: int = 0
        self.kafka_decode_errors_total: int = 0

    @property
    def maxlen(self) -> int:
        return self._maxlen

    async def add(
        self,
        *,
        event: Dict[str, Any],
        source: str,
        signature_valid: Optional[bool] = None,
        raw: Optional[str] = None,
        parse_error: Optional[str] = None,
        ingested_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a record to the store.

        Args:
            event: Parsed audit event payload.
            source: "kafka" or "local".
            signature_valid: Whether the PASETO signature verified.
            raw: Raw message string (optional).
            parse_error: Error message if parsing/verification failed.
            ingested_at: When *this store* ingested the message.
        """
        # Ensure stable identity for de-duplication.
        event_id = str(event.get("event_id") or uuid.uuid4())
        event["event_id"] = event_id

        record: Dict[str, Any] = {
            "event_id": event_id,
            "source": source,
            "signature_valid": signature_valid,
            "parse_error": parse_error,
            "raw": raw,
            "ingested_at": ingested_at or _iso_now(),
            # Flatten common fields for easy filtering.
            "timestamp": event.get("timestamp"),
            "event_type": event.get("event_type"),
            "actor": event.get("actor"),
            "action": event.get("action"),
            "resource": event.get("resource"),
            "correlation_id": event.get("correlation_id"),
            "service": event.get("service"),
            "gateway": event.get("gateway"),
            "request": event.get("request"),
            "details": event.get("details") or {},
            "signature": event.get("signature"),
        }

        async with self._lock:
            if event_id in self._seen_ids:
                # If the Kafka copy arrives later, upgrade the existing local record
                if source == "kafka":
                    for existing in self._events:
                        if existing.get("event_id") == event_id:
                            existing.update(record)   # changes source to kafka + adds raw/signature fields
                            return existing
                return record

            # If the deque is full, evicted items won't be in _events anymore.
            # Clean up _seen_ids lazily when it grows too large.
            self._events.append(record)
            self._seen_ids.add(event_id)
            if len(self._seen_ids) > self._maxlen * 3:
                # Rebuild seen ids from current buffer.
                self._seen_ids = {e["event_id"] for e in self._events}

        return record

    async def list(
        self,
        *,
        limit: int = 200,
        offset: int = 0,
        event_type: Optional[str] = None,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        correlation_id: Optional[str] = None,
        source: Optional[str] = None,
        signature_valid: Optional[bool] = None,
        text: Optional[str] = None,
        time_from: Optional[str] = None,
        time_to: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Query events with simple server-side filters.

        The time_from/time_to are compared as strings (ISO ordering works if both
        are ISO 8601). This keeps the implementation small for MVP.
        """
        et = (event_type or "").lower().strip() or None
        ac = (action or "").lower().strip() or None
        act = (actor or "").lower().strip() or None
        res = (resource or "").strip() or None
        cid = (correlation_id or "").strip() or None
        src = (source or "").lower().strip() or None
        txt = (text or "").lower().strip() or None
        tf = time_from.strip() if isinstance(time_from, str) and time_from.strip() else None
        tt = time_to.strip() if isinstance(time_to, str) and time_to.strip() else None

        async with self._lock:
            items = list(self._events)

        # Sort newest first by timestamp (fallback to ingested_at).
        def sort_key(x: Dict[str, Any]) -> str:
            return str(x.get("timestamp") or x.get("ingested_at") or "")

        items.sort(key=sort_key, reverse=True)

        def match(item: Dict[str, Any]) -> bool:
            if et and _safe_str(item.get("event_type")).lower() != et:
                return False
            if act and _safe_str(item.get("actor")).lower() != act:
                return False
            if ac and _safe_str(item.get("action")).lower() != ac:
                return False
            if res and _safe_str(item.get("resource")) != res:
                return False
            if cid and _safe_str(item.get("correlation_id")) != cid:
                return False
            if src and _safe_str(item.get("source")).lower() != src:
                return False
            if signature_valid is not None and item.get("signature_valid") is not signature_valid:
                return False
            ts = _safe_str(item.get("timestamp") or "")
            if tf and ts and ts < tf:
                return False
            if tt and ts and ts > tt:
                return False
            if txt:
                blob = (
                    _safe_str(item.get("event_type"))
                    + " "
                    + _safe_str(item.get("actor"))
                    + " "
                    + _safe_str(item.get("action"))
                    + " "
                    + _safe_str(item.get("resource"))
                    + " "
                    + _safe_str(item.get("correlation_id"))
                    + " "
                    + _safe_str(item.get("details"))
                ).lower()
                if txt not in blob:
                    return False
            return True

        filtered = [it for it in items if match(it)]
        total = len(filtered)
        # Pagination
        start = max(offset, 0)
        end = start + max(min(limit, 2000), 0)
        return filtered[start:end], total

    async def trace_by_correlation(self, correlation_id: str) -> List[Dict[str, Any]]:
        cid = (correlation_id or "").strip()
        if not cid:
            return []
        async with self._lock:
            items = [e for e in self._events if e.get("correlation_id") == cid]

        items.sort(key=lambda x: str(x.get("timestamp") or x.get("ingested_at") or ""))
        return items

    async def trace_by_resource(self, resource: str) -> List[Dict[str, Any]]:
        res = (resource or "").strip()
        if not res:
            return []
        async with self._lock:
            items = [e for e in self._events if e.get("resource") == res]

        items.sort(key=lambda x: str(x.get("timestamp") or x.get("ingested_at") or ""))
        return items

    async def summary(self) -> Dict[str, Any]:
        async with self._lock:
            items = list(self._events)

        counts: Dict[str, int] = {}
        by_source: Dict[str, int] = {}
        by_action: Dict[str, int] = {}

        for e in items:
            et = str(e.get("event_type") or "unknown")
            counts[et] = counts.get(et, 0) + 1
            src = str(e.get("source") or "unknown")
            by_source[src] = by_source.get(src, 0) + 1
            act = str(e.get("action") or "unknown")
            by_action[act] = by_action.get(act, 0) + 1

        # Recent correlations
        correlations: Dict[str, Dict[str, Any]] = {}
        for e in items:
            cid = e.get("correlation_id")
            if not cid:
                continue
            c = correlations.get(cid)
            ts = str(e.get("timestamp") or e.get("ingested_at") or "")
            if not c:
                correlations[cid] = {
                    "correlation_id": cid,
                    "first_seen": ts,
                    "last_seen": ts,
                    "events": 1,
                    "last_event_type": e.get("event_type"),
                    "last_action": e.get("action"),
                }
            else:
                c["events"] += 1
                if ts < c["first_seen"]:
                    c["first_seen"] = ts
                if ts > c["last_seen"]:
                    c["last_seen"] = ts
                    c["last_event_type"] = e.get("event_type")
                    c["last_action"] = e.get("action")

        recent = sorted(correlations.values(), key=lambda x: x["last_seen"], reverse=True)[:25]

        return {
            "buffer": {"max": self._maxlen, "current": len(items)},
            "counts_by_event_type": counts,
            "counts_by_source": by_source,
            "counts_by_action": by_action,
            "recent_correlations": recent,
            "kafka": {
                "connected": self.kafka_connected,
                "last_ingest_at": self.kafka_last_ingest_at,
                "last_error": self.kafka_last_error,
                "consumed_total": self.kafka_consumed_total,
                "decode_errors_total": self.kafka_decode_errors_total,
            },
        }


# Singleton
audit_store = AuditEventStore()
