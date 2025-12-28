# Runbook: Kafka Unavailable (Audit Pipeline)

## Impact
Audit events may not be produced/consumed. Core auth flows should remain operational.

## Symptoms
- Kafka bootstrap/connect errors in logs
- Audit consumer status indicates disconnected

## Immediate Actions
1. Check Kafka/Zookeeper containers:
   - `docker ps | findstr kafka`
   - `docker ps | findstr zookeeper`
2. Inspect logs:
   - `docker logs disc_kafka --tail 200`
   - `docker logs disc_zookeeper --tail 200`

## Recovery
1. Restart Kafka (and Zookeeper if required):
   - `docker restart disc_zookeeper`
   - `docker restart disc_kafka`
2. Verify topic availability and consumer recovery (if applicable).

## Note
Kafka is treated as a non-critical dependency; degraded mode is acceptable short-term.
