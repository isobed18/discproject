import asyncio
import json
import logging
from typing import Any, Dict, Optional

from aiokafka import AIOKafkaConsumer

from core.config import settings
from core.security import public_key
import pyseto

from services.audit_store import audit_store
from core.metrics import (
    KAFKA_AUDIT_CONSUME_TOTAL,
    KAFKA_AUDIT_DECODE_ERRORS_TOTAL,
    KAFKA_AUDIT_LAST_INGEST_TS,
    now_unix,
)

logger = logging.getLogger(__name__)


class KafkaAuditConsumer:
    """Consumes audit events from Kafka and mirrors them into the in-memory store."""

    def __init__(self):
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    async def start(self):
        # Avoid double-start.
        if self._task:
            return

        self._stop_event.clear()
        try:
            self._consumer = AIOKafkaConsumer(
                settings.KAFKA_TOPIC_AUDIT,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id="disc-admin-ui",
                enable_auto_commit=True,
                auto_offset_reset="latest",
            )
            await self._consumer.start()
            audit_store.kafka_connected = True
            audit_store.kafka_last_error = None
            logger.info("Kafka consumer started.")
        except Exception as e:
            audit_store.kafka_connected = False
            audit_store.kafka_last_error = str(e)
            self._consumer = None
            logger.error(f"Kafka consumer failed to start: {e}")
            return

        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except Exception:
                pass
            self._task = None
        if self._consumer:
            try:
                await self._consumer.stop()
            except Exception:
                pass
            self._consumer = None
        audit_store.kafka_connected = False

    async def _run_loop(self):
        assert self._consumer is not None
        while not self._stop_event.is_set():
            try:
                msg = await self._consumer.getone()
            except asyncio.CancelledError:
                break
            except Exception as e:
                audit_store.kafka_last_error = str(e)
                audit_store.kafka_connected = False
                logger.error(f"Kafka consumer error: {e}")
                await asyncio.sleep(1.0)
                continue

            raw_bytes: bytes = msg.value
            try:
                raw = raw_bytes.decode("utf-8", errors="replace")
            except Exception:
                raw = str(raw_bytes)

            event: Dict[str, Any] = {}
            signature_valid: Optional[bool] = None
            parse_error: Optional[str] = None

            # Try PASETO decode first (preferred path).
            try:
                decoded = pyseto.decode(public_key, raw)
                payload = decoded.payload
                if isinstance(payload, (bytes, bytearray)):
                    payload = payload.decode("utf-8", errors="replace")
                event = json.loads(payload)
                signature_valid = True
            except Exception as e_paseto:
                signature_valid = False
                # Fallback: raw JSON
                try:
                    event = json.loads(raw)
                    parse_error = f"paseto_decode_failed: {e_paseto}"
                except Exception as e_json:
                    event = {
                        "timestamp": None,
                        "event_type": "unparsed_audit_message",
                        "actor": "unknown",
                        "action": "ingest",
                        "resource": "none",
                        "details": {"paseto_error": str(e_paseto), "json_error": str(e_json)},
                        "service": "DISC",
                    }
                    parse_error = f"unparseable: {e_json}"
                    audit_store.kafka_decode_errors_total += 1
                    KAFKA_AUDIT_DECODE_ERRORS_TOTAL.inc()

            audit_store.kafka_consumed_total += 1
            audit_store.kafka_last_ingest_at = datetime_utc_iso()
            KAFKA_AUDIT_CONSUME_TOTAL.inc()
            KAFKA_AUDIT_LAST_INGEST_TS.set(now_unix())

            try:
                await audit_store.add(
                    event=event,
                    source="kafka",
                    signature_valid=signature_valid,
                    raw=raw,
                    parse_error=parse_error,
                )
            except Exception as e:
                logger.error(f"Failed to add audit event to store: {e}")


def datetime_utc_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


kafka_audit_consumer = KafkaAuditConsumer()
