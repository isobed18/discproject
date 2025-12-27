# Developer Onboarding Guide

This repo contains a small "DISC Coupon Authority" stack:

- **backend/**: Coupon Authority (FastAPI) – `/v1/issue`, `/v1/verify`, `/v1/revoke`, `/v1/public-key`
- **gateway/**: Sidecar gateway that validates coupons then proxies to an upstream service
- **sdk/**: Python SDK (`DiscClient`) + local cache/offline support
- **cli/**: CLI wrapper on top of the SDK
- **frontend/**: Optional UI

## Prerequisites

- Python 3.11+
- (Optional) Docker if you want to run Redis/OPA/Kafka locally

## Install Python dependencies

From the repo root:

```bash
python -m venv .venv
# Linux/Mac:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

pip install -r requirements.txt
```

## Run the Coupon Authority (backend)

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Health check:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/v1/health
```

## Run a demo upstream service

A small upstream FastAPI app lives under `sample_app/upstream_service.py`:

```bash
uvicorn sample_app.upstream_service:app --host 0.0.0.0 --port 8001 --reload
```

## Run the gateway

```bash
# In another terminal
export CA_BASE_URL=http://localhost:8000/v1
export UPSTREAM_BASE_URL=http://localhost:8001

uvicorn gateway.main:app --host 0.0.0.0 --port 8002 --reload
```

Now:
- `http://localhost:8002/health` is unprotected
- Any other path will require `Authorization: Bearer <coupon>`

## Use the CLI

Mint a coupon:

```bash
python cli/disc-cli.py --url http://localhost:8000/v1 mint --audience app-srv --scope "GET /hello" --ttl 300
```

Verify it:

```bash
python cli/disc-cli.py --url http://localhost:8000/v1 verify <COUPON>
```

Call the upstream through the gateway:

```bash
curl -H "Authorization: Bearer <COUPON>" http://localhost:8002/hello
```

## Offline mode (SDK/CLI)

The SDK supports two offline strategies:

- `cache`: if the CA is unreachable, return a previously cached verification result (until the token expires)
- `local`: verify the PASETO signature locally using the CA public key

Local verification needs a stable public key. You can:

1) Fetch it from the CA:

```bash
python cli/disc-cli.py --url http://localhost:8000/v1 public-key
```

2) Then enable offline mode:

```bash
python cli/disc-cli.py --url http://localhost:8000/v1 --offline --offline-strategy local verify <COUPON>
```

Tip: for local verification to work across restarts, configure the CA with a stable private key:

- `PASETO_PRIVATE_KEY_PEM` (PEM string)
- or `PASETO_PRIVATE_KEY_PATH` (file path)

## Troubleshooting

- **403 purpose_mismatch**: The gateway expects the coupon `scope` to match the request method+path. Example: for `GET /hello`, issue a coupon with scope `"GET /hello"`.
- **503 coupon_authority_unavailable**: Backend not running or wrong `CA_BASE_URL`.
- **Corrupt cache**: Delete `~/.disc/cache.json`.
