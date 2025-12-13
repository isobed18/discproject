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

### 1. Delegation (Yetki Devri)
Allows a user to temporarily grant access to their resource to another user.

**Bash / CMD:**
```bash
curl -X POST "http://localhost:8000/v1/delegations" \
     -H "Content-Type: application/json" \
     -d '{"delegate": "test-user", "resource": "secure-doc-1", "ttl": 3600}'
```

**PowerShell:**
*(Using native PowerShell command which is more reliable for JSON)*
```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/v1/delegations" `
     -ContentType "application/json" `
     -Body '{"delegate": "test-user", "resource": "secure-doc-1", "ttl": 3600}'
```

**Verification:** Now `test-user` can request a coupon for `secure-doc-1`.
```bash
# Bash
curl -X POST "http://localhost:8000/v1/issue" \
     -H "Content-Type: application/json" \
     -d '{"audience": "app-srv", "scope": "read", "resource": "secure-doc-1"}'
```
```powershell
# PowerShell
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/v1/issue" `
     -ContentType "application/json" `
     -Body '{"audience": "app-srv", "scope": "read", "resource": "secure-doc-1"}'
```

### 2. Partial Evaluation (Toplu Kontrol)
Ask the system: "Which of these resources can I access?" efficiently.
*Note: This endpoint mocks the requester as `test-user` for demonstration purposes.*

**Bash / CMD:**
```bash
curl -X POST "http://localhost:8000/v1/filter-authorized" \
     -H "Content-Type: application/json" \
     -d '{"resources": ["secure-doc-1", "forbidden-doc-99"], "action": "read", "audience": "app-srv"}'
```

**PowerShell:**
```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/v1/filter-authorized" `
     -ContentType "application/json" `
     -Body '{"resources": ["secure-doc-1", "forbidden-doc-99"], "action": "read", "audience": "app-srv"}'
```
*Result:* Should return `["secure-doc-1"]` (since we delegated it to `test-user`). `forbidden-doc-99` should be absent.

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

