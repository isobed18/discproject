# PERSON A (CORE SERVICES LEAD) - PRESENTATION NOTES

## 🔑 Your Core Responsibilities (The "Engine")

1.  **The Protocol (Usage Protocol)**: You designed the **Coupon Schema** (V1). Not just a token, but a signed capability (PASETO).
2.  **Core APIs**: You built the high-performance `Issue`, `Verify`, and `Revoke` endpoints.
3.  **Identity Pipeline**: You integrated OIDC (Google/Okta) and mTLS so we know WHO is calling us.
4.  **Sub-Coupons (Scope)**: You allowed coupons to be "scoped" (e.g., User -> App -> Service).

---

## 🛠️ Feature Verification (The "Proof")

### 1. Coupon Schema (PASETO V4)
*   **Concept**: We don't use JWT (unsafe). We use **PASETO** (Platform-Agnostic Security Tokens).
*   **Proof**:
    *   Show Code: `backend/core/security.py`
    *   Highlight: `pyseto.encode(..., footer={"kid": "v4.public"})`
    *   Explain: "No alg header attacks. Secure by default."

### 2. Issuance Flow (The Heartbeat)
*   **Concept**: Fast, stateless issuance.
*   **Proof**:
    *   **Action**: Run `python scripts/demo_mint.py`.
    *   **Result**: Shows a signed coupon. "This is not just a string, it's a verifiable promise."

### 3. Authentication (OIDC + mTLS)
*   **Concept**: Defense in Depth.
*   **Proof**:
    *   Show Code: `backend/api/endpoints.py` -> `issue_coupon`.
    *   Logic: Checks `Bearer` token (OIDC) OR `x-client-cert-hash` (mTLS). "If you don't have an ID, you are anonymous."

### 4. Revocation (Kill Switch)
*   **Concept**: Everything breaks? Revoke it.
*   **Proof**:
    *   **Action**: Use Postman/Curl to call `/revoke`.
    *   **Backend**: Checks Redis.
    *   **Code**: `backend/services/revocation.py` -> `is_jti_revoked`.

---

## 📋 Checklist Status (Your Parts)

| Feature | Status | Where is it? |
| :--- | :--- | :--- |
| **Schema V1** | ✅ DONE | `backend/core/security.py` |
| **Issue/Verify API** | ✅ DONE | `backend/api/endpoints.py` |
| **Revocation (Redis)** | ✅ DONE | `backend/services/revocation.py` |
| **OIDC Middleware** | ✅ DONE | `backend/main.py` |
| **Correlation IDs** | ✅ DONE | `backend/middleware/correlation.py` |

---

## 🎯 Demo Flow
1.  **Intro**: "I built the Core Engine. The V8 of this car."
2.  **Code**: Show `models.py` (The Contract).
3.  **Action**: Mint a token. "See how fast that was?"
4.  **Revoke**: "Now I kill it." (Call Revoke endpoint).
5.  **Verify**: "Now I try to use it... Rejected."
6.  **Conclusion**: "Reliable, Fast, Secure."
