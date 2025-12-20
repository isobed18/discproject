# Incident Response Playbook

## Scenario 1: Key Compromise (Private Key Leaked)
**Severity:** CRITICAL
**Steps:**
1. **Rotate Keys Immediately**: Restart Backend to generate new Ed25519 keys (for MVP memory keys). For production, update Vault.
2. **Revoke Active Coupons**: 
    - Identify coupons signed by old key (search audit logs).
    - Issue generic revocation or flush Redis cache if necessary.
3. **Notify Users**: Send alert to rely on new keys.

## Scenario 2: OPA Unavailable
**Severity:** HIGH
**Symptoms**: Endpoints return `503 Service Unavailable`.
**Steps:**
1. Check Docker status: `docker ps | grep opa`.
2. Restart OPA: `docker restart disc-opa`.
3. Check Policy: `curl localhost:8181/v1/policies`.
4. Re-upload Policy if missing:
   `curl -X PUT --data-binary @backend/policies/main.rego "http://localhost:8181/v1/policies/disc"`

## Scenario 3: PII Leak in Logs
**Severity:** HIGH
**Steps:**
1. **Verify Encryption**: Check `backend/core/config.py` has `FIELD_ENCRYPTION_KEY`.
2. **Purge**: Delete specific keys in Redis (`audit:msg:{id}`) containing cleartext.
3. **Patch**: Ensure `AuditService` encrypts the specific field.
