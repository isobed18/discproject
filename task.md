# Project Verification & Documentation Task List

## 🚀 Phase 1: Clean Up & Commit (Person D Complete)
- [x] Fix Backend Audit Search API (`backend/api/endpoints.py`)
- [x] Add `/audit-events` endpoint for Frontend compatibility
- [x] Verify Audit Logs flow (Mint -> API -> Kafka/Redis -> Frontend)
- [x] Create Person D Presentation Notes (`docs/PERSON_D_PRESENTATION_NOTES.md`)
- [x] Update Person D QA Script (`docs/DEMO_QA_PERSON_D.txt`)
- [ ] Commit all fixes with detailed message

## 👤 Phase 2: Person A (Core Services)
- [ ] **Verify Week 1-6 Tasks** (from `6weekcomp.txt`)
    - [ ] Coupon Schema & API (Issue/Verify/Revoke)
    - [ ] OIDC + mTLS Auth
    - [ ] Sub-coupons & Scopes
    - [ ] Performance (Review metrics/profiling if available)
- [ ] **Create Documentation**
    - [ ] `docs/PERSON_A_PREP_CHECKLIST.txt`
    - [ ] `docs/DEMO_QA_PERSON_A.txt`
    - [ ] `docs/PERSON_A_PRESENTATION_NOTES.md`

## 🛠️ Phase 3: Person B (DevOps/SRE)
- [ ] **Verify Week 1-6 Tasks**
    - [ ] K8s/Docker Stack (Redis, Kafka, OPA)
    - [ ] CI/CD Pipelines
    - [ ] Observability (Prometheus/Grafana/Loki)
    - [ ] Reliability (Chaos tests, backups - verify artifacts/scripts)
- [ ] **Create Documentation**
    - [ ] `docs/PERSON_B_PREP_CHECKLIST.txt`
    - [ ] `docs/DEMO_QA_PERSON_B.txt`
    - [ ] `docs/PERSON_B_PRESENTATION_NOTES.md`

## 💻 Phase 4: Person C (SDKs & Gateway)
- [ ] **Verify Week 1-6 Tasks**
    - [ ] CLI Tool (`disc-cli.py`)
    - [ ] SDKs (Python/Node/Go - check `sdk/` folder)
    - [ ] Gateway Logic (Inbound/Outbound checks)
    - [ ] Admin UI (React App)
- [ ] **Create Documentation**
    - [ ] `docs/PERSON_C_PREP_CHECKLIST.txt`
    - [ ] `docs/DEMO_QA_PERSON_C.txt`
    - [ ] `docs/PERSON_C_PRESENTATION_NOTES.md`

## ✅ Phase 5: Final Review
- [ ] Ensure all 6-week goals in `6weekcomp.txt` are marked as complete or noted as mocked/simulated.
