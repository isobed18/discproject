# Project Verification & Documentation Task List

## 🚀 Phase 1: Clean Up & Commit (Person D Complete)
- [x] Fix Backend Audit Search API (`backend/api/endpoints.py`)
- [x] Add `/audit-events` endpoint for Frontend compatibility
- [x] Verify Audit Logs flow (Mint -> API -> Kafka/Redis -> Frontend)
- [x] Create Person D Presentation Notes (`docs/PERSON_D_PRESENTATION_NOTES.md`)
- [x] Update Person D QA Script (`docs/DEMO_QA_PERSON_D.txt`)
- [x] Commit all fixes with detailed message

## 👤 Phase 2: Person A (Core Services)
- [x] **Verify Week 1-6 Tasks** (from `6weekcomp.txt`)
    - [x] Coupon Schema & API (Issue/Verify/Revoke)
    - [x] OIDC + mTLS Auth
    - [x] Sub-coupons & Scopes
    - [x] Performance (Review metrics/profiling if available)
- [x] **Create Documentation**
    - [x] `docs/PERSON_A_PREP_CHECKLIST.txt`
    - [x] `docs/DEMO_QA_PERSON_A.txt`
    - [x] `docs/PERSON_A_PRESENTATION_NOTES.md`

## 🛠️ Phase 3: Person B (DevOps/SRE)
- [x] **Verify Week 1-6 Tasks**
    - [x] K8s/Docker Stack (Redis, Kafka, OPA)
    - [x] CI/CD Pipelines
    - [x] Observability (Prometheus/Grafana/Loki)
    - [x] Reliability (Chaos tests, backups - verify artifacts/scripts)
- [x] **Create Documentation**
    - [x] `docs/PERSON_B_PREP_CHECKLIST.txt`
    - [x] `docs/DEMO_QA_PERSON_B.txt`
    - [x] `docs/PERSON_B_PRESENTATION_NOTES.md`

## 💻 Phase 4: Person C (SDKs & Gateway)
- [x] **Verify Week 1-6 Tasks**
    - [x] CLI Tool (`disc-cli.py`)
    - [x] SDKs (Python/Node/Go - check `sdk/` folder)
    - [x] Gateway Logic (Inbound/Outbound checks)
    - [x] Admin UI (React App)
- [x] **Create Documentation**
    - [x] `docs/PERSON_C_PREP_CHECKLIST.txt`
    - [x] `docs/DEMO_QA_PERSON_C.txt`
    - [x] `docs/PERSON_C_PRESENTATION_NOTES.md`

## ✅ Phase 5: Final Review
- [x] Ensure all 6-week goals in `6weekcomp.txt` are marked as complete or noted as mocked/simulated.
