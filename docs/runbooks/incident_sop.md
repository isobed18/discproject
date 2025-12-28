# Incident SOP (DISC)

## Severity Levels
- SEV1: Widespread auth failures or suspected compromise
- SEV2: Partial outage (e.g., audit pipeline down)
- SEV3: Minor degradation, no security impact

## Triage Checklist
1. Confirm scope: which endpoints/operations are affected?
2. Check recent deploys/changes.
3. Review metrics:
   - auth deny spikes
   - latency p95 increases
   - dependency unavailable counters
4. Review logs with correlation IDs to reconstruct end-to-end flow.

## Containment
- Prefer fail-closed paths for authorization
- Revoke suspicious coupons (blacklist JTI if supported)
- Rotate keys if compromise suspected (KMS-backed rotation)

## Eradication & Recovery
- Restore critical dependencies (OPA/Redis/Kafka)
- Validate core flows: issue -> verify -> revoke
- Confirm audit visibility restored

## Post-Incident
- Write a short postmortem: timeline, root cause, blast radius, remediation actions
- Add regression test / runbook improvement
