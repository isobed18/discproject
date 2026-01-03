# PERSON D (SECURITY LEAD) - PRESENTATION NOTES

This document is your **personal cheat sheet** for the presentation. It defines only YOUR contributions.

---

## 🔑 Your Core Responsibilities (The "Why")

1.  **Authorization (Who can do what?)**: You moved from hardcoded `if user == admin` checks to a dynamic **Policy Engine (OPA)**.
2.  **Auditability (What happened?)**: You ensured every action is logged, signed, and immutable (cannot be deleted/fake).
3.  **Data Protection (Safe Storage)**: You encrypted sensitive fields (PII) in the database so even DB admins can't read them.
4.  **Resilience (Staying Alive)**: You implemented Rate Limiting to stop DoS attacks.

---

## 🛠️ Feature Verification (The "Proof")

### 1. OPA Policy Engine (Authorization)
*   **Concept**: Decoupling code from policy. "Policy as Code".
*   **What you did**: Created `main.rego` policy files.
*   **Proof**:
    *   Show File: `backend/policies/main.rego`
    *   Command (Load Policy):
        ```bash
        curl -X PUT --data-binary @backend/policies/main.rego http://localhost:8181/v1/policies/disc/authz
        ```

### 2. Secure Audit Logs (Non-Repudiation)
*   **Concept**: Immutable logs. If a log is changed, the signature breaks.
*   **What you did**: Implemented PASETO signing for every log entry.
*   **Proof**:
    *   **Action**: Run `python scripts/demo_mint.py`.
    *   **Check**: Go to Frontend -> Audit Logs. Show the "Signature" field in the JSON details.
    *   **Backend Code**: `backend/services/audit.py` (Search for `pyseto.encode`).

### 3. Encryption at Rest (Data Privacy)
*   **Concept**: Defense in Depth. Even if DB is leaked, PII is safe.
*   **What you did**: Field-level encryption using Fernet (AES).
*   **Proof**:
    *   Show Code: `backend/core/security.py` -> `encrypt_field` function.
    *   Explain: "Whenever we save `details` to the database, we run this function."

### 4. Rate Limiting (Hardening)
*   **Concept**: Preventing abuse/DoS.
*   **What you did**: Added `SlowAPI` middleware.
*   **Proof**:
    *   **Action**: Spam the health endpoint.
        ```bash
        1..10 | % { Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get }
        ```
    *   **Result**: You will see `429 Too Many Requests` after 5 attempts.

---

## 📋 Checklist Status (Your Parts Only)

| Feature | Status | Where is it? |
| :--- | :--- | :--- |
| **Policy Model** | ✅ DONE | `backend/policies/main.rego` |
| **Secure Logging** | ✅ DONE | `backend/services/audit.py` (Kafka Producer) |
| **Delegation** | ✅ DONE | `backend/services/delegation.py` |
| **Audit Search** | ✅ DONE | `POST /audit/search` |
| **Encryption** | ✅ DONE | `backend/core/security.py` |
| **Rate Limiting** | ✅ DONE | `backend/core/limiter.py` |
| **Playbooks** | ✅ DONE | `docs/incident_playbook.md` |

---

## 🎯 Demo Flow (Summary)

1.  **Intro**: "I am Person D, I built the Security Architecture."
2.  **OPA**: Show rego file -> Load it.
3.  **Flow**: Run `scripts/demo_mint.py` -> Token generated -> API accepted -> Log created.
4.  **Audit**: Show log in UI -> Point to Signature.
5.  **Attack**: Run Rate Limit script -> Show 429 error.
6.  **Conclusion**: "System is secure by design."
