# Security Model

## STRIDE Risk Analysis

### Spoofing
- **Threat**: Attacker impersonates a legitimate service to obtain coupons.
- **Mitigation**: mTLS for all service-to-service communication. CA validates client certificates against a trusted root.

### Tampering
- **Threat**: Attacker modifies a coupon to elevate privileges.
- **Mitigation**: Coupons are signed using PASETO v4 (Ed25519). Any modification invalidates the signature.

### Repudiation
- **Threat**: A user denies performing an action.
- **Mitigation**: Immutable audit logs. Every issuance is signed and logged. Every verification is logged. Logs are stored in a write-once database or forwarded to a secure SIEM.

### Information Disclosure
- **Threat**: Attacker reads sensitive data from the coupon.
- **Mitigation**: PASETO v4.public is signed but not encrypted. Sensitive data should not be put in the coupon. If needed, use v4.local (encrypted). For now, we assume coupons contain only non-sensitive claims (scopes, audience).

### Denial of Service
- **Threat**: Attacker floods the CA with requests.
- **Mitigation**: Rate limiting (Redis-backed). Short-lived coupons reduce the window for replay attacks, but high issuance rate is needed. Caching verification results can reduce load.

### Elevation of Privilege
- **Threat**: Attacker uses a valid coupon for an unauthorized purpose.
- **Mitigation**: Scope-bound coupons. Resource servers enforce scope checks. OPA policies define what scopes a client can request.

## OPA Policy Layout

We use Open Policy Agent (OPA) to decide if a client is allowed to mint a specific coupon.

### Policy Structure
```rego
package disc.authz

default allow = false

# Allow if the client is in the allowed_clients list for the requested scope
allow {
    input.method == "POST"
    input.path == "/issue"
    is_allowed_client(input.client_id, input.requested_scope)
}

is_allowed_client(client, scope) {
    data.policies[scope].allowed_clients[_] == client
}
```

## Immutable Audit Log Format

Audit logs are JSON objects, potentially signed or chained.

```json
{
  "id": "log-uuid-123",
  "timestamp": "2023-10-27T10:00:00Z",
  "event_type": "coupon_issued",
  "actor": {
    "id": "service:frontend",
    "ip": "10.0.0.1"
  },
  "action": {
    "type": "issue",
    "target": "service:backend"
  },
  "resource": {
    "jti": "coupon-uuid-456",
    "scope": "read:data"
  },
  "context": {
    "request_id": "req-789"
  },
  "signature": "base64-signature-of-content"
}
```
