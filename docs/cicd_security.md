# CI/CD Secure Supply Chain

## Overview
We implement a secure software supply chain to ensure the integrity of the DISC platform artifacts.

## SBOM Generation
- **Tool**: Syft or Trivy.
- **Process**: Generated during the container build process.
- **Storage**: Stored alongside the container image in the registry or as a separate artifact.

## Cosign Signing
- **Tool**: Sigstore Cosign.
- **Process**:
    1. Build container image.
    2. Generate key pair (or use KMS).
    3. Sign the image digest: `cosign sign --key <key> <image-uri>`.
    4. Verify signature at deployment time (Admission Controller).

## Pipeline Security
- **Runners**: Ephemeral, isolated runners.
- **Secrets**: Injected via Vault or GitHub Secrets (never hardcoded).
- **Linting**: Pre-commit hooks for secrets detection (gitleaks) and code quality.
