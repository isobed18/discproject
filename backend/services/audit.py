import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from aiokafka import AIOKafkaProducer
import pyseto

from core.config import settings
from core.security import private_key, encrypt_field
from services.audit_store import audit_store
from services.audit_indexer import audit_indexer

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
            
        await audit_indexer.connect()

    async def stop(self):
        """Stops the Kafka producer."""
        if self.producer:
            try:
                await self.producer.stop()
                logger.info("Kafka Producer stopped.")
            except Exception:
                pass
        await audit_indexer.close()

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
        
        # Week 4: PII Protection (Encryption at Rest)
        # We encrypt specific keys in 'details' known to contain PII
        safe_details = details or {}
        pii_fields = {"email", "phone", "address", "pii_data"}
        
        encrypted_details = {}
        for k, v in safe_details.items():
            if k in pii_fields and isinstance(v, str):
                encrypted_details[k] = "enc:" + encrypt_field(v)
            else:
                encrypted_details[k] = v

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
            "details": encrypted_details, # Use encrypted version
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
            
        # Index in Redis (Week 4)
        await audit_indexer.index_event(event_data)

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
