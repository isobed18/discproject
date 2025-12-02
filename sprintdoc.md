# Sprint 1: Foundational Design & Architecture

## Scope and Goals
The primary goal of Sprint 1 is to establish the foundational design, architecture, and initial tooling for the DISC project. We aim to define the core mechanisms for the Coupon Authority and set up the necessary infrastructure and development environment.

## Planned Work Items
### Design & Architecture
- [x] **Design the Coupon Authority Core**: Operation-based, short-lived, PoP bound, sub-scopeable, revocation-supported.
- [x] **Define Core Contracts**: Coupon Schema (v1), API contracts, Security architecture.
- [x] **Establish Standards**: mTLS + OIDC flows, Redis/Postgres architecture, Revocation cache strategy.
- [x] **Define Security Model**: STRIDE analysis, OPA policy layout, Immutable audit log format.

### Tooling & Infrastructure
- [x] **Initialize Tooling**: Base UI project (React/TS), CLI prototype.
- [x] **Deploy Core Infrastructure**: K8s cluster definition, Core components (Vault, Kafka, Redis, Postgres, etc.).

## Increment Log
- **Week 1**: Completed foundational design, standards, and initial tooling/infra setup.
- **Week 2 (MVP)**: Implemented Coupon Authority MVP with `/issue`, `/verify`, `/revoke` endpoints. Integrated Redis for revocation. Implemented PASETO v4 signing and PoP validation.

## Sprint Retrospective
*(To be updated at the end of the sprint)*
