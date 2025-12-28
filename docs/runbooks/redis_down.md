# Runbook: Redis Unavailable (Revocation/Delegation Store)

## Impact
Revocation/delegation lookups fail. Some operations may be rejected (fail-closed).

## Symptoms
- Redis connection errors in backend logs
- Coupon issuance may fail if delegation checks depend on Redis

## Immediate Actions
1. Check Redis container:
   - `docker ps | findstr redis`
2. Inspect Redis logs:
   - `docker logs disc_redis --tail 200`
3. Verify Redis connectivity (from host):
   - `docker exec -it disc_redis redis-cli PING`

## Recovery
1. Restart Redis:
   - `docker restart disc_redis`
2. Re-run critical flows (issue/verify/revoke) and confirm expected behavior.

## Data Note
If persistence is disabled, revocation state may be volatile; document this operational risk.
