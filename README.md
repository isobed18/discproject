# DISC (Digital Identity Disc & Short-Lived Capability Coupons)

DISC is a next-generation authorization framework designed to move away from long-lived static credentials (like API Keys or long-lived JWTs). Instead, it issues **short-lived, operation-specific "permission coupons"** that are cryptographically signed and verified before every action.

This project implements the **Coupon Authority (CA)**, the central service responsible for issuing, verifying, and revoking these coupons.

---

## 🏗️ Architecture & Components

The project is composed of several key components working together:

1.  **Backend (Coupon Authority Core)**:
    *   Built with **Python FastAPI**.
    *   Handles cryptographic signing (PASETO v4) and verification.
    *   Enforces policies (OPA-style) before issuing coupons.
    *   Manages the revocation list (Redis) and audit logs.

2.  **Frontend (Admin Console)**:
    *   Built with **React & TypeScript**.
    *   Provides a dashboard for administrators to view audit logs and manually revoke coupons.

3.  **CLI (Command Line Interface)**:
    *   A Python-based tool for developers and CI/CD pipelines to interact with the CA (Mint, Verify, Revoke).

4.  **SDK (Software Development Kit)**:
    *   A Python library (`disc_sdk`) that simplifies integrating DISC into other applications.

---

## 📂 Project Structure Explained

Here is a breakdown of the codebase for new contributors:

*   **`backend/`**: The core API server.
    *   `main.py`: Entry point of the application. Sets up the API and CORS.
    *   `api/`: Contains the REST API definitions.
        *   `endpoints.py`: Defines `/issue`, `/verify`, `/revoke` routes.
        *   `models.py`: Pydantic models defining the request/response schemas.
    *   `core/`: Core logic and configuration.
        *   `security.py`: Handles PASETO v4 signing/verification, Key management, OIDC token decoding, and mTLS header extraction.
        *   `config.py`: Loads environment variables (Redis URL, Secret Keys).
    *   `services/`: Business logic services.
        *   `revocation.py`: Manages the communication with Redis for checking revoked tokens.
*   **`frontend/`**: The Admin UI.
    *   `src/App.tsx`: Main React component containing the logic for fetching logs and revoking tokens.
*   **`cli/`**:
    *   `disc-cli.py`: The script that runs the CLI commands. It uses the SDK internally.
*   **`sdk/`**:
    *   `disc_sdk/client.py`: The Python client library that wraps HTTP calls to the backend.
*   **`docs/`**: Documentation files (Security, Backup strategies).

---

## 🚀 Getting Started

### Prerequisites
*   **Python 3.11+**
*   **Node.js 18+**
*   **Redis** (Optional for local dev, the system falls back to in-memory mock if Redis is missing).

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/isobed18/discproject.git
    cd discproject
    ```

2.  **Backend Setup**:
    ```bash
    cd backend
    pip install -r requirements.txt
    ```

3.  **Frontend Setup**:
    ```bash
    cd frontend
    npm install
    ```

### Running the Project

1.  **Start the Backend**:
    ```bash
    # From the root directory
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
    ```
    The API will be available at `http://localhost:8000`.

2.  **Start the Frontend**:
    ```bash
    # From the frontend directory
    cd frontend
    npm run dev
    ```
    The UI will be available at `http://localhost:5173`.

---

## ✅ Project Status & Verification
This project has completed deliverables for **Weeks 1-6** (Security Persona).
- Full Status Checklist: [COMPLETION_CHECKLIST.md](COMPLETION_CHECKLIST.md)
- Handover Report: [docs/HANDOVER.md](docs/HANDOVER.md)

To verify the entire system functionality:
```bash
python scripts/verify_all.py
```

---

## 🛡️ OPA Policy Engine Setup (Important)

> [!IMPORTANT]
> **OPA Feature was missing for initial MVP.**
> Please use this version of `main` from now on. Everybody should pull the new `main` immediately to ensure consistency.

The project now integrates **Open Policy Agent (OPA)** for authorization decisions.

### 1. Running OPA Locally
To enforce policies strictly, you must run an OPA server. The easiest way is via Docker:

```bash
docker run -p 8181:8181 openpolicyagent/opa:latest-static run --server --addr :8181
```

### 2. Uploading Policies
Once OPA is running, upload the Rego policy:

**Bash / Command Prompt:**
```bash
curl -X PUT --data-binary @backend/policies/main.rego http://localhost:8181/v1/policies/disc/authz
```

**PowerShell (Windows):**
In PowerShell, `curl` is an alias for `Invoke-WebRequest`, which has different syntax. Use `curl.exe` explicitly if you have Git installed, or use:
```powershell
Invoke-RestMethod -Method PUT -Uri "http://localhost:8181/v1/policies/disc/authz" -Body (Get-Content backend/policies/main.rego -Raw)
```

### 3. Disabling Dev Mode
By default, the backend runs in `DEV_MODE=True`, which **allows** requests even if OPA is down (Fail-Open).
To test actual enforcement:
1.  Open `backend/core/config.py`.
2.  Set `DEV_MODE = False`.
3.  Restart the backend.

Now, if OPA is not running or the policy denies access, your requests will be rejected (403 Forbidden).

---

## 🧪 Testing New Features (Week 3)

We have implemented **Delegation** and **Partial Evaluation**.

## 🧪 Testing New Features (Week 3 - Production Flow)

We have implemented **Delegation** and **Partial Evaluation**.
To test these features robustly (mimicking production), we must use **Authentication Tokens (OIDC)**.

### Prerequisites (Generate Token)
Since we don't have a real Identity Provider (IdP) for local dev, generating a valid token is necessary. We provided a helper script:

```bash
# Generate a token for user "ali"
python cli/create_test_token.py ali
# Output example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```
*Save this token as `$TOKEN` (bash) or `$env:TOKEN` (PowerShell).*

### 1. Delegation (Yetki Devri)
Grant access to "ali".
*Note: Any authorized user (or system admin) can create delegations.*

**Bash:**
```bash
curl -X POST "http://localhost:8000/v1/delegations" \
     -H "Content-Type: application/json" \
     -d '{"delegate": "ali", "resource": "secure-doc-1", "ttl": 3600}'
```

**PowerShell:**
```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/v1/delegations" `
     -ContentType "application/json" `
     -Body '{"delegate": "ali", "resource": "secure-doc-1", "ttl": 3600}'
```

### 2. Partial Evaluation (With Token)
Now, call the endpoint **AS "ali"** using the token.

**Bash:**
```bash
curl -X POST "http://localhost:8000/v1/filter-authorized" \
     -H "Authorization: Bearer <PASTE_TOKEN_HERE>" \
     -H "Content-Type: application/json" \
     -d '{"resources": ["secure-doc-1", "forbidden-doc-99"], "action": "read", "audience": "app-srv"}'
```

**PowerShell:**
```powershell
$Token = python cli/create_test_token.py ali
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/v1/filter-authorized" `
     -Headers @{Authorization=("Bearer " + $Token)} `
     -ContentType "application/json" `
     -Body '{"resources": ["secure-doc-1", "forbidden-doc-99"], "action": "read", "audience": "app-srv"}'
```
*Result:* Returns `["secure-doc-1"]` because OPA sees the token belongs to `ali` and `ali` has a delegation.

### 3. Issue Coupon (With Token)
Obtain the final PASETO coupon for the resource.

**PowerShell:**
```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/v1/issue" `
     -Headers @{Authorization=("Bearer " + $Token)} `
     -ContentType "application/json" `
     -Body '{"audience": "app-srv", "scope": "read", "resource": "secure-doc-1"}'
```

---

## 📖 Usage Guide
By default, the backend runs in `DEV_MODE=True`, which **allows** requests even if OPA is down (Fail-Open).
To test actual enforcement:
1.  Open `backend/core/config.py`.
2.  Set `DEV_MODE = False`.
3.  Restart the backend.

Now, if OPA is not running or the policy denies access, your requests will be rejected (403 Forbidden).

---

## 📖 Usage Guide

### 1. Using the CLI
The CLI is the easiest way to interact with the system.

*   **Mint (Issue) a Coupon**:
    Creates a new coupon for a specific audience and scope.
    ```bash
    python cli/disc-cli.py mint --audience my-service --scope read:data --ttl 300
    ```
    *Returns*: A JSON object containing the signed `coupon` string.

*   **Verify a Coupon**:
    Checks if a coupon is valid, not expired, and not revoked.
    ```bash
    python cli/disc-cli.py verify "v4.public.YOUR_COUPON_STRING..."
    ```

*   **Revoke a Coupon**:
    Invalidates a coupon using its JTI (ID).
    ```bash
    python cli/disc-cli.py revoke "COUPON_JTI_UUID"
    ```

### 2. API Endpoints

*   **`POST /v1/issue`**
    *   **Purpose**: Issues a new PASETO coupon.
    *   **Headers**:
        *   `Authorization`: Bearer <OIDC_TOKEN> (Optional, identifies the caller).
        *   `X-Client-Cert-Hash`: <SHA256> (Optional, binds coupon to mTLS cert).
    *   **Body**:
        ```json
        {
          "audience": "target-service",
          "scope": "read:data",
          "ttl_seconds": 300
        }
        ```

*   **`POST /v1/verify`**
    *   **Purpose**: Verifies a coupon.
    *   **Body**: `{"coupon": "v4.public..."}`
    *   **Response**: Returns the claims if valid, or an error.

*   **`POST /v1/revoke`**
    *   **Purpose**: Revokes a coupon.
    *   **Body**: `{"jti": "uuid...", "reason": "compromised"}`

*   **`GET /v1/audit-logs`**
    *   **Purpose**: Returns a list of all issuance and revocation events.

---

## 🔒 Security Features Implemented

1.  **PASETO v4 (Public)**: We use Asymmetric Ed25519 keys for signing. This ensures that only the CA can issue coupons, but anyone with the public key can verify them.
2.  **Proof-of-Possession (PoP)**: If an `X-Client-Cert-Hash` header is present during issuance, it is embedded in the token (`cnf` claim). The receiver should verify that the client presenting the token matches this hash.
3.  **OIDC Integration**: The system accepts standard OIDC tokens (like from Auth0 or Keycloak) to identify *who* is requesting a coupon.
4.  **Policy Enforcement (OPA)**:
    *   **Open Policy Agent** integration for fine-grained authorization logic.
    *   **Delegation Rules**: Supports delegation of authority (e.g., User A can act on behalf of User B for specific resources) via Rego policies.
    *   **Dev Mode**: Fail-open fallback for local development without OPA.

## 📊 Observability & Operational Maturity (Week 4)

This project aims not only for functional correctness but also for production-like operational behavior.  
During Week 4, the system was elevated to an **operational maturity** level.

---

### 🔍 Metrics (Prometheus)

The backend exposes Prometheus-compatible metrics via the following endpoint:

* **GET /metrics**

Key collected metrics include:

* **disc_coupon_issue_total** — total number of issued coupons
* **disc_issue_latency_seconds** — coupon issuance latency
* **disc_revoke_total** — total number of revoked coupons
* **disc_policy_deny_total** — requests denied by OPA policies

---

### 📈 Grafana Dashboard Examples

* **Coupon Issue Rate**

```
rate(disc_coupon_issue_total[1m])
```

* **p95 Latency**

```
histogram_quantile(
  0.95,
  sum(rate(disc_issue_latency_seconds_bucket[5m])) by (le)
)
```

* **Revocation Freshness**

```
time() - disc_last_revoke_timestamp
```

These dashboards enable observation of system behavior under load, authorization latency, and the consistency of the revocation mechanism.

---

### 🛡️ Fail-Closed Security Behavior

Since the system relies on an external **Open Policy Agent (OPA)** for authorization decisions, it exhibits the following security behavior:

* If OPA is unreachable → **/v1/issue → 503 Service Unavailable**
* If OPA is reachable but denies the request → **403 Forbidden**
* When **DEV_MODE = False**, the default behavior is **fail-closed**

This approach prevents accidental privilege escalation and enforces **secure-by-default** principles.

---

## 🛡️ Security & Compliance (Week 4-6)

### 1. Audit Indexing & Search
The system now persists audit logs to Redis and provides a search API.
- **Search**: `GET /v1/audit/search?actor=...`
- **RBAC**: Requires Admin privileges.

### 2. Data Protection (PII)
Sensitive fields (email, phone, address) in audit logs are **encrypted at rest** using AES-GCM (Fernet) before being allocated to storage or Kafka.

### 3. Hardening
- **Rate Limiting**: Integrated `slowapi`. Default limits apply.
- **Security Headers**: HSTS, CSP, and X-Content-Type-Options are enforced via middleware.
- **Vulnerability Scanning**: Use `scripts/security_scan.ps1` to run Bandit and Safety scans.

### 4. Governance
Refer to `docs/` for:
- [Compliance Checklist](docs/compliance_checklist.md) (SOC2/ISO)
- [Incident Playbook](docs/incident_playbook.md) (SOPs)

