import asyncio
import json
import base64
from aiokafka import AIOKafkaConsumer
from core.config import settings

# Renkli çıktılar
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

async def monitor_signatures():
    print(f"{YELLOW}--- CANLI İMZA TAKİP SİSTEMİ (PACKET SNIFFER) ---{RESET}")
    print(f"📡 Kafka Sunucusu: {settings.KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Topic: {settings.KAFKA_TOPIC_AUDIT}")
    print("--------------------------------------------------")

    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC_AUDIT,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="live-demo-sniffer-v2", 
        auto_offset_reset="latest"
    )

    await consumer.start()
    
    try:
        print(f"{GREEN}✅ Sniffer Aktif! Paket bekleniyor...{RESET}\n")
        
        async for msg in consumer:
            if not msg.value: continue

            # Veriyi al
            try:
                raw_str = msg.value.decode('utf-8').strip()
            except:
                raw_str = str(msg.value)

            payload = {}
            source_type = "❓ Bilinmiyor"
            
            # --- MANUEL PASETO AYRIŞTIRMA (HACK) ---
            # Format: v4.public.<payload_base64>.<footer_base64>
            if raw_str.startswith("v4.public."):
                try:
                    parts = raw_str.split(".")
                    if len(parts) >= 3:
                        body_b64 = parts[2]
                        
                        # Base64 Padding düzeltmesi
                        body_b64 += "=" * ((4 - len(body_b64) % 4) % 4)
                        
                        # Base64 Decode (URL safe)
                        decoded_bytes = base64.urlsafe_b64decode(body_b64)
                        
                        # PASETO v4.public yapısı: [Message] + [64 byte Signature]
                        # Sondaki 64 byte imzayı atıp mesaja ulaşıyoruz
                        if len(decoded_bytes) > 64:
                            message_bytes = decoded_bytes[:-64]
                            payload_str = message_bytes.decode('utf-8')
                            payload = json.loads(payload_str)
                            source_type = "🔓 PASETO (Decoded via Sniffing)"
                        else:
                            raise ValueError("Paket çok kısa")
                    else:
                        raise ValueError("Eksik parça")

                except Exception as e:
                    # Başarısız olursa JSON dene
                    try:
                        payload = json.loads(raw_str)
                        source_type = "📄 JSON (Ham)"
                    except:
                        print(f"{RED}❌ Veri okunamadı: {raw_str[:30]}...{RESET}")
                        continue
            else:
                # PASETO değilse JSON dene
                try:
                    payload = json.loads(raw_str)
                    source_type = "📄 JSON (Ham)"
                except:
                    continue

            # --- EKRANA BASMA ---
            event_type = payload.get("event_type", "Bilinmiyor")
            signature = payload.get("signature", "⚠️ İMZA YOK")
            actor = payload.get("actor", "anonim")
            timestamp = payload.get("timestamp", "Zaman Yok")

            print(f"{CYAN}CAPTURE TIME: {timestamp}{RESET}")
            print(f"Event: {event_type} | Actor: {actor} | Type: {source_type}")
            
            if signature != "⚠️ İMZA YOK":
                print(f"{YELLOW}🔐 HMAC SIGNATURE:{RESET}")
                print(f"{GREEN}{signature}{RESET}")
            else:
                print(f"{RED}⚠️ DİKKAT: İMZA EKSİK!{RESET}")
                
            print("-" * 60)

    except KeyboardInterrupt:
        print("\n🛑 İzleme sonlandırıldı.")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(monitor_signatures())