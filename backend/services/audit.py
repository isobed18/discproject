import json
import threading
import time
from datetime import datetime, timezone
from ..core.config import settings

# Windows dostu kütüphane: kafka-python
try:
    from kafka import KafkaProducer, KafkaConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    print("⚠️ kafka-python bulunamadı! 'pip install kafka-python' çalıştırın.")

audit_logs = []

class AuditLogger:
    def __init__(self):
        self.producer = None
        self.running = False
        self.use_kafka = False
        self.consumer_thread = None

    async def start(self):
        self.running = True
        if not KAFKA_AVAILABLE:
            return

        try:
            # Producer Başlat
            self.producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                # Timeout süresini kısalttık ki sunucuyu yormasın
                request_timeout_ms=2000 
            )
            
            # Consumer'ı Ayrı Thread'de Başlat
            self.consumer_thread = threading.Thread(target=self.consume_logs_sync, daemon=True)
            self.consumer_thread.start()
            
            self.use_kafka = True
            print("✅ Kafka Connected Successfully (Sync Driver)!")
        except Exception as e:
            print(f"⚠️ Kafka Connection Failed: {e}")
            self.use_kafka = False

    async def stop(self):
        self.running = False
        if self.producer:
            self.producer.close()

    async def log_event(self, event_type: str, actor: str, action: str, resource: str, details: dict = None):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "actor": actor,
            "action": action,
            "resource": resource,
            "details": details or {}
        }

        # 1. Hafızaya ekle (Hız için)
        audit_logs.insert(0, log_entry)
        if len(audit_logs) > 100: audit_logs.pop()

        # 2. Kafka'ya gönder (Kayıt için)
        if self.use_kafka and self.producer:
            try:
                # DÜZELTME BURADA: .future ile gönderiyoruz ama sonucu beklemiyoruz (Non-blocking)
                self.producer.send(settings.KAFKA_TOPIC_AUDIT, log_entry)
                
                # ❌ self.producer.flush()  <-- BU SATIRI SİLDİK! (Donmaya sebep oluyordu)
                
            except Exception as e:
                print(f"❌ Kafka Send Error: {e}")

    def consume_logs_sync(self):
        if not self.use_kafka: return
        try:
            time.sleep(2) 
            consumer = KafkaConsumer(
                settings.KAFKA_TOPIC_AUDIT,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                auto_offset_reset='earliest',
                group_id="disc-backend-group-sync",
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            for message in consumer:
                if not self.running: break
                pass
        except Exception as e:
            # Arka planda sessizce kalsın, sunucuyu etkilemesin
            pass

audit_logger = AuditLogger()