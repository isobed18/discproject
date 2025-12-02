# API Contracts & Coupon Schema (v1)

## Coupon Schema (v1)

We use PASETO v4 (Public) for the coupon.

### Header
- `v4.public`

### Payload (Claims)
```json
{
  "iss": "https://auth.disc.local",       // Issuer
  "sub": "user:12345",                    // Subject (User or Service ID)
  "aud": "service:document-store",        // Audience
  "exp": "2023-10-27T10:15:00Z",          // Expiration (ISO 8601 or Unix Timestamp)
  "nbf": "2023-10-27T10:00:00Z",          // Not Before
  "iat": "2023-10-27T10:00:00Z",          // Issued At
  "jti": "a1b2c3d4-e5f6-...",             // Unique Coupon ID (UUID)
  "scope": "read:doc:123 write:doc:123",  // Space-separated permissions
  "cnf": {                                // Confirmation (PoP)
    "x5t#S256": "base64url-encoded-hash"  // SHA-256 thumbprint of client cert
  }
}
```

## API Endpoints

Base URL: `https://auth.disc.local/v1`

### 1. Issue Coupon
**POST** `/issue`

**Description**: Mint a new coupon for the authenticated client.

**Headers**:
- `Authorization`: `Bearer <OIDC_TOKEN>` (if applicable, or rely on mTLS identity)
- `X-Client-Cert`: (Handled by mTLS termination, passed as header if needed)

**Request Body**:
```json
{
  "audience": "service:document-store",
  "scope": "read:doc:123",
  "ttl_seconds": 300 // Optional, capped by policy
}
```

**Response (200 OK)**:
```json
{
  "coupon": "v4.public.eyJ...",
  "expires_in": 300,
  "jti": "a1b2c3d4..."
}
```

**Errors**:
- `400 Bad Request`: Invalid input.
- `401 Unauthorized`: Authentication failed.
- `403 Forbidden`: Policy denies issuance.

### 2. Verify Coupon
**POST** `/verify`

**Description**: Verify a coupon's validity (signature, expiration, revocation).
*Note: Resource servers should ideally verify locally using the public key and local revocation cache, but this endpoint exists for centralized verification or debugging.*

**Request Body**:
```json
{
  "coupon": "v4.public.eyJ..."
}
```

**Response (200 OK)**:
```json
{
  "valid": true,
  "claims": { ... }
}
```

**Response (200 OK - Invalid)**:
```json
{
  "valid": false,
  "error": "expired" // or "revoked", "signature_invalid"
}
```

### 3. Revoke Coupon
**POST** `/revoke`

**Description**: Revoke a coupon before its expiration.

**Headers**:
- `Authorization`: `Bearer <ADMIN_TOKEN>`

**Request Body**:
```json
{
  "jti": "a1b2c3d4...",
  "reason": "compromise_suspected"
}
```

**Response (200 OK)**:
```json
{
  "status": "revoked",
  "revoked_at": "2023-10-27T10:05:00Z"
}
```

## Security Architecture

### Authentication
- **mTLS**: All service-to-service communication (including to the CA) is secured via mTLS. The CA extracts the client identity from the certificate Subject Name or SAN.
- **OIDC**: Human users or external clients may authenticate via OIDC (e.g., Keycloak/Google). The OIDC token is exchanged for a Coupon.

### Trust
- **Root of Trust**: The CA's signing key is the root of trust for coupons.
- **Key Rotation**: Signing keys are rotated periodically. Old keys are retained for verification until all coupons signed by them expire.

### Revocation
- **Storage**: Redis is used for storing the revocation list (JTI + Expiration).
- **Strategy**: When a coupon is revoked, its JTI is added to Redis with a TTL equal to the coupon's remaining validity.
