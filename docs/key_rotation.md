# Key Rotation Strategy

## PASETO v4 Public Keys
We use Ed25519 keys for signing tokens. Keys must be rotated periodically (e.g., every 90 days) or immediately upon compromise.

## Rotation Process
1.  **Generate New Key Pair**:
    - Create `v4.public.2.pem` and `v4.private.2.pem`.
2.  **Deploy New Private Key**:
    - Update the **Backend** config to use the new Private Key for *signing* new tokens.
    - *Note*: The Backend should strictly use the new key for issuance.
3.  **Distribute New Public Key**:
    - Publish the new Public Key to the JWKS endpoint or distribute to services.
    - Services (Verifiers) must be able to trust **BOTH** the old key (Version 1) and the new key (Version 2) during the transition.
4.  **Wait for TTL**:
    - Wait for the max token TTL (e.g., 1 hour) so that all tokens signed with Key V1 expire.
5.  **Deprecate Old Key**:
    - Remove Key V1 from the trusted list in Verifiers.
    - Archive the old private key.

## Emergency Rotation
In case of private key compromise:
1.  Immediately revoke all tokens (Global Revocation).
2.  Deploy new keys to all services instantly.
3.  Restart services if necessary to flush caches.
