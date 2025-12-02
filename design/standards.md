# Technical Standards

## Authentication Flows

### mTLS (Machine-to-Machine)
1. **Handshake**: Client and Server perform mutual TLS handshake.
2. **Validation**: Server validates Client's certificate against the internal CA bundle.
3. **Identity Extraction**: Server extracts the SPIFFE ID or Subject Name from the certificate.
4. **Binding**: This identity is used to bind the issued coupon (via `cnf` claim).

### OIDC (User-to-Machine)
1. **Login**: User logs in via an Identity Provider (e.g., Keycloak).
2. **Token Exchange**: User's client exchanges the ID Token for a Coupon via the `/issue` endpoint.
3. **Validation**: CA validates the ID Token signature and claims.
4. **Issuance**: CA issues a coupon bound to the user's identity.

## Infrastructure Architecture

### Database (PostgreSQL)
- **Purpose**: Persistent storage for:
    - Audit Logs (immutable append-only).
    - Policy definitions.
    - Long-term revocation records (archived).
- **Schema**:
    - `audit_logs`: `id`, `timestamp`, `actor`, `action`, `resource`, `context`, `signature`.
    - `policies`: `id`, `name`, `rego_content`, `version`.

### Cache (Redis)
- **Purpose**: High-performance storage for:
    - Active Revocation List (Blacklist).
    - Rate limiting counters.
    - Short-lived ephemeral state.
- **Revocation Strategy**:
    - Key: `revoked:<jti>`
    - Value: `reason`
    - TTL: `coupon_exp - current_time` (Auto-expiry).

### Revocation Cache Strategy
- **Write**: When a coupon is revoked, write to Redis immediately.
- **Read**: During verification, check Redis for `revoked:<jti>`.
- **Fall-back**: If Redis is unavailable, fail closed (deny access) or fall back to DB (slower).
- **Consistency**: Redis is the source of truth for active revocations.

## Observability
- **Metrics**: Prometheus (latency, error rates, issuance counts).
- **Logs**: Loki (structured JSON logs).
- **Traces**: OpenTelemetry (end-to-end request tracing).
