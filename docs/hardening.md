# Week 5 – Hardening & Chaos Testing

## Scope
This week focused on validating system resilience and fail-closed security behavior
under dependency failures.

---

## Test 1: Redis Failure (Revocation & Delegation Store)

### Objective
Verify that the system behaves in a fail-closed manner when Redis becomes unavailable.

### Test Method
- Redis container was intentionally stopped using Docker.
- Coupon issuance endpoint was invoked during Redis outage.
- Backend health and logs were observed.

### Expected Result
- Backend remains operational.
- Redis-dependent operations fail safely.
- No security bypass or silent allow occurs.

### Observed Result
- Backend returned controlled error responses.
- Redis connection error was logged.
- Backend process did not crash.
- Health endpoint remained responsive.

### Conclusion
Fail-closed security behavior and controlled degradation were successfully validated.

---

## Test 2: Kafka Failure (Audit Pipeline)

### Objective
Ensure audit pipeline failure does not affect core authorization paths.

### Test Method
- Kafka container was intentionally stopped.
- Coupon issuance and verification endpoints were invoked.

### Expected Result
- Core authorization remains functional.
- Audit ingestion degrades gracefully.
- No impact on security enforcement.

### Observed Result
- Backend remained operational.
- Audit consumer logged connection errors.
- Authorization paths continued to function.

### Conclusion
Kafka is correctly treated as a non-critical dependency.

---

## Multi-AZ Readiness (Conceptual Validation)

- Backend service is stateless.
- Configuration is environment-based.
- Service restart does not affect system security guarantees.

This demonstrates readiness for multi-instance or multi-AZ deployment.
