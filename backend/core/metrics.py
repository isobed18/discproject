import time
from prometheus_client import Counter, Histogram, Gauge

# Counters
COUPON_ISSUE_TOTAL = Counter(
    "disc_coupon_issue_total",
    "Total number of issued coupons"
)

COUPON_VERIFY_TOTAL = Counter(
    "disc_coupon_verify_total",
    "Total number of verified coupons"
)

COUPON_REVOKE_TOTAL = Counter(
    "disc_coupon_revoke_total",
    "Total number of revoked coupons"
)

OPA_DENY_TOTAL = Counter(
    "disc_opa_deny_total",
    "Total number of authorization denials by OPA/policy"
)

OPA_UNAVAILABLE_TOTAL = Counter(
    "disc_opa_unavailable_total",
    "Total number of times OPA was unavailable (fail-closed path)"
)

# Latency histograms
ISSUE_LATENCY_SECONDS = Histogram(
    "disc_issue_latency_seconds",
    "Latency for /v1/issue operations",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5)
)

VERIFY_LATENCY_SECONDS = Histogram(
    "disc_verify_latency_seconds",
    "Latency for /v1/verify operations",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5)
)

REVOKE_LATENCY_SECONDS = Histogram(
    "disc_revoke_latency_seconds",
    "Latency for /v1/revoke operations",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5)
)

# Revoke freshness (seconds since last revoke)
LAST_REVOKE_TS = Gauge(
    "disc_last_revoke_timestamp",
    "Unix timestamp of the last revoke event"
)

# --- Week 4: Low-cardinality HTTP + Kafka observability ---
# NOTE: Keep label cardinality low in Prometheus.
HTTP_REQUESTS_TOTAL = Counter(
    "disc_http_requests_total",
    "Total number of HTTP requests handled by DISC backend",
    labelnames=("route", "method", "status"),
)

HTTP_REQUEST_LATENCY_SECONDS = Histogram(
    "disc_http_request_latency_seconds",
    "HTTP request latency (seconds)",
    labelnames=("route", "method"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)

KAFKA_AUDIT_CONSUME_TOTAL = Counter(
    "disc_kafka_audit_consume_total",
    "Total number of audit messages consumed from Kafka",
)

KAFKA_AUDIT_DECODE_ERRORS_TOTAL = Counter(
    "disc_kafka_audit_decode_errors_total",
    "Total number of Kafka audit messages that failed to decode/parse",
)

KAFKA_AUDIT_LAST_INGEST_TS = Gauge(
    "disc_kafka_audit_last_ingest_timestamp",
    "Unix timestamp of last consumed audit message",
)

def now_unix() -> float:
    return time.time()
