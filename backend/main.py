from contextlib import asynccontextmanager
import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

# --- ENTRY POINT: ABSOLUTE IMPORTS ONLY ---
# Do not use relative imports (dots) in this file.
from core.config import settings
from api import endpoints
from services.audit import audit_service
from services.kafka_audit_consumer import kafka_audit_consumer
from core.metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_LATENCY_SECONDS


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


@app.middleware("http")
async def correlation_and_metrics_middleware(request: Request, call_next):
    # Correlation-ID (end-to-end traceability)
    correlation_id = (
        request.headers.get("x-correlation-id")
        or request.headers.get("x-request-id")
        or str(uuid.uuid4())
    )
    request.state.correlation_id = correlation_id

    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
    finally:
        route = _derive_route_label(request.url.path)
        HTTP_REQUESTS_TOTAL.labels(route=route, method=request.method, status=str(status_code)).inc()
        HTTP_REQUEST_LATENCY_SECONDS.labels(route=route, method=request.method).observe(
            max(time.perf_counter() - start, 0)
        )

    response.headers["x-correlation-id"] = correlation_id
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For MVP/Dev purposes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(endpoints.router, prefix=settings.API_V1_STR)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
