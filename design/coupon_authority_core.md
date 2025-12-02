# Coupon Authority Core Design

## Overview
The Coupon Authority is the central component responsible for issuing, verifying, and revoking short-lived capability coupons. It enforces the "least privilege" and "zero-trust" principles by ensuring that every action is authorized by a valid, specific, and traceable coupon.

## Core Principles

### 1. Operation-Based
Coupons are not generic session tokens. They are bound to specific operations or sets of operations.
- **Granularity**: Permissions are defined at the operation level (e.g., `read:user:123`, `write:document:456`).
- **Intent**: The coupon represents the intent to perform an action.

### 2. Short-Lived
Coupons have a very short Time-To-Live (TTL).
- **Duration**: Typically measured in minutes (e.g., 5-15 minutes).
- **Renewal**: Clients must request new coupons for subsequent operations or use a refresh mechanism if applicable (though the goal is to minimize long-lived credentials).

### 3. Proof-of-Possession (PoP) Bound
Coupons are bound to the holder's identity or a cryptographic key to prevent theft and replay attacks.
- **Binding**: The coupon contains a claim (e.g., `cnf` - confirmation) that links it to a client's public key or mTLS certificate hash.
- **Validation**: The verifying service checks that the presenter possesses the corresponding private key (e.g., via mTLS or a signed request).

### 4. Sub-Scopeable
Coupons can be attenuated or restricted further.
- **Delegation**: A service holding a coupon can issue a derived coupon with a subset of permissions to a downstream service.
- **Constraints**: Additional constraints (e.g., IP address, time window) can be added.

### 5. Revocation-Supported
Despite being short-lived, coupons must be revocable.
- **Mechanism**: A revocation list (or bloom filter) is maintained for active coupons.
- **Check**: Verification involves checking the revocation status.
- **Latency**: Revocation propagation should be near real-time.

## Architecture

### Coupon Format
We will use **PASETO** (Platform-Agnostic Security Tokens) for the coupon format due to its security and simplicity compared to JWT.
- **Version**: v4 (Public) or v2.
- **Payload**:
    - `iss`: Issuer (Coupon Authority)
    - `sub`: Subject (User or Service ID)
    - `aud`: Audience (Target Service)
    - `exp`: Expiration Time
    - `nbf`: Not Before Time
    - `iat`: Issued At Time
    - `jti`: Unique Coupon ID (Nonce)
    - `scope`: List of permissions
    - `cnf`: Confirmation key (for PoP)

### Issuance Flow
1. **Authentication**: Client authenticates via mTLS + OIDC.
2. **Request**: Client requests a coupon for specific operations.
3. **Policy Check**: Authority checks OPA policies to see if the client is allowed to request these permissions.
4. **Minting**: Authority mints a signed PASETO coupon.
5. **Logging**: Issuance event is logged to the immutable audit log.

### Verification Flow
1. **Presentation**: Client presents the coupon to the Resource Server.
2. **Signature Check**: Resource Server verifies the PASETO signature.
3. **PoP Check**: Resource Server verifies the client's PoP (e.g., mTLS cert matches `cnf`).
4. **Revocation Check**: Resource Server checks the revocation cache (Redis).
5. **Expiration Check**: Resource Server checks `exp`.
6. **Scope Check**: Resource Server checks if `scope` covers the requested operation.

### Revocation Flow
1. **Trigger**: Admin or automated system triggers revocation for a `jti` or `sub`.
2. **Update**: Authority updates the revocation list in Redis.
3. **Propagation**: Revocation events are published to a message queue (Kafka) for other components to consume (if local caching is used).
