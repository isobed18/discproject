import uvicorn
import sys
import asyncio

# WINDOWS İÇİN ZORUNLU AYAR
# Uvicorn başlamadan önce Loop politikasını değiştiriyoruz.
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if __name__ == "__main__":
    print("🚀 Sunucu Başlatılıyor (Windows Fix Aktif)...")
    # reload=False yapıyoruz çünkü reload Windows'ta Kafka'yı koparıyor.
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)