import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any
from aiokafka import AIOKafkaProducer
import pyseto

# --- DÜZELTME: Absolute Import (Noktaları kaldırdık) ---
# Docker "/app" klasörünü ana klasör gördüğü için direkt isimleriyle çağırıyoruz:
from core.config import settings
from core.security import private_key

logger = logging.getLogger(__name__)

class AuditService:
    def __init__(self):
        self.producer = None
        self.topic = settings.KAFKA_TOPIC_AUDIT

    async def start(self):
        """Starts the Kafka producer."""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS
            )
            await self.producer.start()
            logger.info("Kafka Producer started successfully.")
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            self.producer = None

    async def stop(self):
        """Stops the Kafka producer."""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka Producer stopped.")

    async def log_event(self, event_type: str, actor: str, action: str, resource: str, details: Dict[str, Any] = None):
        """
        Signs the event payload and publishes it to Kafka.
        """
        event_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "actor": actor,
            "action": action,
            "resource": resource,
            "details": details or {},
            "service": settings.PROJECT_NAME
        }

        # 1. Sign the event (Non-repudiation)
        try:
            signed_token = pyseto.encode(
                private_key,
                event_data,
                footer={"kid": "v4.public"}
            )
            message_bytes = signed_token.encode("utf-8")
        except Exception as e:
            logger.error(f"Failed to sign audit event: {e}")
            message_bytes = json.dumps(event_data).encode("utf-8")

        # 2. Publish to Kafka
        if self.producer:
            try:
                await self.producer.send_and_wait(self.topic, message_bytes)
                logger.info(f"Audit event sent to Kafka: {event_type}")
            except Exception as e:
                logger.error(f"Failed to send to Kafka: {e}")
        else:
            logger.warning("Kafka producer not available, skipping audit log.")

# Singleton instance
audit_service = AuditService()