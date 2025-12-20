# DISC Auth Governance & Compliance Checklist

## Security & Access Control (SOC 2 CC6)
- [x] **Authentication**: OIDC integration enforced (Week 3).
- [x] **Authorization**: OPA policies for RBAC (Week 3).
- [x] **Key Management**: Ed25519 keys generated (Week 1). Rotation documented (Week 3).
- [x] **Encryption**: PII is encrypted at rest (Week 4).
- [x] **Rate Limiting**: Applied to sensitive endpoints (Week 5).

## Monitoring & Audit (SOC 2 CC7)
- [x] **Audit Logging**: Immutable events sent to Kafka (Week 4).
- [x] **Traceability**: Correlation-IDs propagated (Week 1).
- [x] **Search**: Admin tool for audit logs (Week 4).

## Availability & Recovery (SOC 2 CC9)
- [ ] **Disaster Recovery**: Redis RDB/AOF not yet configured (Person B task).
- [ ] **Backups**: Database backup schedule (Person B task).

## Incident Response (SOC 2 CC7.3)
- [x] Playbooks defined (`docs/incident_playbook.md` - In Progress).
- [ ] On-call rotation defined (Person B task).
