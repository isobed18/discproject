# Diğer importlar ayar yapıldıktan SONRA gelmeli
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .core.config import settings
from .api import endpoints
from .services.audit import audit_logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to Kafka
    print("🚀 Starting Audit System (Kafka)...")
    try:
        await audit_logger.start()
        # Bağlantı başarılı olsa bile log basalım
    except Exception as e:
        print(f"⚠️ Kafka Connection Failed: {e}")
    
    yield
    
    # Shutdown: Disconnect
    print("🛑 Stopping Audit System...")
    await audit_logger.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(endpoints.router, prefix=settings.API_V1_STR)

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    # Loop ayarını burada yapmıyoruz, en tepede yaptık.
    # Reload kapalı çalıştıracağız.
    uvicorn.run(app, host="0.0.0.0", port=8000)