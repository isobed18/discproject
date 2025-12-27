# Test Scenarios

These scenarios are intended as a lightweight checklist for manual or scripted verification.

## Core issuance & verification

1. **Issue**
   - Request: `POST /v1/issue` with `audience`, `scope`, and optional `ttl_seconds`.
   - Expected: `200` with `{coupon, expires_in, jti}`.

2. **Verify (valid)**
   - Request: `POST /v1/verify` with `coupon`.
   - Expected: `200` and `{valid: true, claims: {...}}`.

3. **Verify (invalid)**
   - Request: `POST /v1/verify` with a corrupted token.
   - Expected: `200` and `{valid: false, error: "..."}`.

4. **Revoke**
   - Request: `POST /v1/revoke` with a known `jti`.
   - Expected: `200` and `{status: "revoked", revoked_at: "..."}`.

5. **Verify revoked**
   - Request: `POST /v1/verify` with a token that was revoked.
   - Expected: `200` and `{valid: false, error: "Token is revoked"}`.

## Gateway scenarios

1. **Unprotected endpoints**
   - `GET /health` via gateway should return `200` without `Authorization`.

2. **Missing coupon**
   - Request any non-unprotected path via gateway without `Authorization`.
   - Expected: `401` with `{detail: "missing_coupon"}`.

3. **Invalid coupon**
   - Provide `Authorization: Bearer <garbage>`.
   - Expected: `403` with `{detail: "invalid_coupon"}`.

4. **Purpose binding**
   - Issue coupon with scope `"GET /hello"`.
   - Call `GET /hello` through gateway.
   - Expected: `200`.
   - Call `GET /resource/abc` with the same coupon.
   - Expected: `403` with `{detail: "purpose_mismatch"}`.

## SDK resilience

1. **Retry/backoff**
   - Simulate CA returning `503` or `429`.
   - Expected: SDK retries up to `max_retries`.

2. **Cache verify results**
   - Verify a valid coupon once (online).
   - Stop the CA (or break network).
   - Call `verify_coupon()` with `offline=True` and `offline_strategy=cache`.
   - Expected: cached valid response (until coupon expires).

3. **Offline local verification**
   - Ensure CA has a stable signing key (set `PASETO_PRIVATE_KEY_PEM` or `PASETO_PRIVATE_KEY_PATH`).
   - Fetch public key once (`GET /v1/public-key`).
   - Stop the CA.
   - Run SDK with `offline=True` and `offline_strategy=local`.
   - Expected: local verification succeeds for a non-expired token.
