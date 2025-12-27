"""Demo upstream service.

Run:
  uvicorn sample_app.upstream_service:app --port 8001 --reload

Then use the gateway to protect it:
  CA_BASE_URL=http://localhost:8000/v1 UPSTREAM_BASE_URL=http://localhost:8001 \
    uvicorn gateway.main:app --port 8002 --reload

Call:
  curl -H "Authorization: Bearer <coupon>" http://localhost:8002/hello
"""

from fastapi import FastAPI, Request

app = FastAPI(title="DISC Demo Upstream")


@app.get("/hello")
async def hello(request: Request):
    # The gateway may attach coupon claims to headers if you later extend it.
    return {
        "message": "hello from upstream",
        "path": str(request.url.path),
    }


@app.get("/resource/{rid}")
async def resource(rid: str):
    return {"resource_id": rid, "status": "ok"}
