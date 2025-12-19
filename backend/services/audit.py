import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from aiokafka import AIOKafkaProducer
import pyseto

from core.config import settings
from core.security import private_key
from services.audit_store import audit_store

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.topic = settings.KAFKA_TOPIC_AUDIT

    async def start(self):
        """Starts the Kafka producer."""
        try:
            self.producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
            await self.producer.start()
            logger.info("Kafka Producer started successfully.")
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            self.producer = None

    async def stop(self):
        """Stops the Kafka producer."""
        if self.producer:
            try:
                await self.producer.stop()
                logger.info("Kafka Producer stopped.")
            except Exception:
                pass

    async def log_event(
        self,
        event_type: str,
        actor: str,
        action: str,
        resource: str,
        details: Optional[Dict[str, Any]] = None,
        *,
        correlation_id: Optional[str] = None,
        gateway: Optional[Dict[str, Any]] = None,
        request: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """Create a signed audit event and publish it to Kafka.

        Week 4: This is also mirrored into an in-memory store so the Admin UI
        can render events even when Kafka is unavailable in local dev.
        """

        event_data: Dict[str, Any] = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "actor": actor,
            "action": action,
            "resource": resource,
            "correlation_id": correlation_id,
            "gateway": gateway,
            "request": request,
            "details": details or {},
            "service": settings.PROJECT_NAME,
        }
        if extra:
            # Non-breaking enrichment field.
            event_data["extra"] = extra

        # Mirror locally (best-effort)
        try:
            await audit_store.add(event=event_data, source="local", signature_valid=None, raw=None, parse_error=None)
        except Exception as e:
            logger.debug(f"Audit store mirror failed: {e}")

        # 1) Sign the event (Non-repudiation)
        try:
            signed_token = pyseto.encode(private_key, event_data, footer={"kid": "v4.public"})
            if isinstance(signed_token, (bytes, bytearray)):
                message_bytes = signed_token
            else:
                message_bytes = str(signed_token).encode("utf-8")
        except Exception as e:
            logger.error(f"Failed to sign audit event: {e}")
            message_bytes = json.dumps(event_data).encode("utf-8")

        # 2) Publish to Kafka
        if self.producer:
            try:
                await self.producer.send_and_wait(self.topic, message_bytes)
                logger.info(f"Audit event sent to Kafka: {event_type}")
            except Exception as e:
                logger.error(f"Failed to send to Kafka: {e}")
        else:
            logger.warning("Kafka producer not available, skipping audit publish.")


# Singleton instance
audit_service = AuditService()
