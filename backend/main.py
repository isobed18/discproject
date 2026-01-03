from contextlib import asynccontextmanager
import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

# --- ENTRY POINT: ABSOLUTE IMPORTS ONLY ---
# Do not use relative imports (dots) in this file.
from core.config import settings
from api import endpoints, audit
from services.audit import audit_service
from services.kafka_audit_consumer import kafka_audit_consumer
from core.metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_LATENCY_SECONDS
from core.middleware_security import SecurityHeadersMiddleware

# Week 5: Rate Limiting
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from core.limiter import limiter


def _derive_route_label(path: str) -> str:
    # Keep labels low-cardinality for Prometheus.
    if path.startswith(f"{settings.API_V1_STR}/issue"):
        return "issue"
    if path.startswith(f"{settings.API_V1_STR}/verify"):
        return "verify"
    if path.startswith(f"{settings.API_V1_STR}/revoke"):
        return "revoke"
    if path.startswith(f"{settings.API_V1_STR}/audit"):
        return "audit"
    if path.startswith(f"{settings.API_V1_STR}/trace"):
        return "trace"
    if path.startswith(f"{settings.API_V1_STR}/consumer"):
        return "consumer"
    return "other"


# Lifespan context manager to handle startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start Kafka producer and consumer
    await audit_service.start()
    await kafka_audit_consumer.start()
    
    yield
    # Shutdown: Stop Kafka consumer and producer
    await kafka_audit_consumer.stop()
    await audit_service.stop()



app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Week 5: Register Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Week 5: Security Headers
app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For MVP/Dev purposes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(endpoints.router, prefix=settings.API_V1_STR)
app.include_router(audit.router, prefix=settings.API_V1_STR)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


@app.middleware("http")
async def correlation_and_metrics_middleware(request: Request, call_next):
    """
    Correlation ID ve Metrik Middleware'i
    Gelen istekte 'X-Correlation-ID' varsa onu kullanır, yoksa yeni üretir.
    """
    import uuid
    
    # 1. MİSAFİR KARTI KONTROLÜ (Gelen ID var mı?)
    # Header'dan 'x-correlation-id' veya 'X-Correlation-ID' okumaya çalış
    correlation_id = request.headers.get("x-correlation-id") or request.headers.get("X-Correlation-ID")
    
    # 2. Yoksa yeni kart bas (UUID)
    if not correlation_id:
        correlation_id = str(uuid.uuid4())

    # 3. Bu ID'yi Context'e işle (Loglama için)
    request.state.correlation_id = correlation_id
    
    # ContextVar güncelle (Loglarda görünmesi için)
    # (Eğer projenin core/logging.py yapısında contextvar varsa burası otomatik işler)
    
    # 4. İsteği Devam Ettir (Zaman ölçümü)
    start_time = time.time()
    try:
        response = await call_next(request)
    except Exception as e:
        # Hata durumunda bile süreyi ölç
        process_time = time.time() - start_time
        # Hataları logla (Opsiyonel)
        raise e

    process_time = time.time() - start_time
    
    # 5. Cevaba ID'yi ekle (Frontend görsün diye)
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Process-Time"] = str(process_time)
    
    return response