# Observability and Policy Enforcement Infrastructure
*(Prometheus, Grafana, Open Policy Agent)*

## 1. Purpose

The DISC (Digital Identity & Short-Lived Coupon) system relies on fine-grained,
short-lived authorization decisions. For such a system, **observability** and
**policy enforcement transparency** are critical.

The goal of this work is to ensure that:
- Authorization decisions are traceable and auditable
- Policy denials can be detected in real time
- System behavior can be monitored under normal and failure conditions
- The system is operationally ready for production-like environments

This document describes the integration of **Open Policy Agent (OPA)**,
**Prometheus**, and **Grafana** as part of the Week 3–4 implementation.

---

## 2. Architecture Overview

The observability and policy infrastructure consists of three main components:

- **Open Policy Agent (OPA)**  
  Responsible for policy-based authorization decisions (allow / deny).

- **Prometheus**  
  Collects and stores time-series metrics exposed by backend services.

- **Grafana**  
  Visualizes metrics and provides operational dashboards.

The DISC backend exposes Prometheus-compatible metrics via the `/metrics`
endpoint and consults OPA before performing any security-sensitive operation.

---

## 3. Open Policy Agent (OPA)

### 3.1 Role in the System

OPA acts as the **Policy Decision Point (PDP)** for the DISC system.
Before issuing, verifying, or revoking a coupon, the backend sends a policy
evaluation request to OPA.

The system follows two core security principles:
- **Default-deny**: all requests are denied unless explicitly allowed
- **Fail-closed**: if OPA is unavailable, requests are denied

### 3.2 Policy Evaluation Flow

For each protected operation, the backend provides OPA with:
- HTTP method and request path
- Subject identity (`sub`)
- Requested scope
- Target resource
- Delegation context (if applicable)

OPA evaluates the input and returns a boolean authorization decision.

### 3.3 Validation

The following scenarios were tested:
- Unauthorized requests are denied by policy
- Requests remain denied when OPA is unavailable
- Denied requests are recorded as audit and metric events

This confirms correct enforcement of policy-driven authorization.

---

## 4. Prometheus Integration

### 4.1 Purpose

Prometheus is used to quantitatively observe system behavior and security events.
It enables monitoring of both functional and security-related aspects of DISC.

### 4.2 Exposed Metrics

The backend exposes a `/metrics` endpoint containing custom metrics, including:
- Coupon issuance, verification, and revocation counters
- Policy denial counters
- HTTP request counts and latency histograms
- Rate-limiting and error indicators

Example metrics:
- `disc_coupon_issue_total`
- `disc_opa_deny_total`
- `disc_http_requests_total`
- `disc_issue_latency_seconds`

### 4.3 Scraping Configuration

Prometheus periodically scrapes metrics from the backend service:

```yaml
scrape_configs:
  - job_name: "disc-backend"
    static_configs:
      - targets:
          - "host.docker.internal:8000"
