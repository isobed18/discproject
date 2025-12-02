# DISC (Digital Identity Disc & Short-Lived Capability Coupons)

DISC is a secure, auditable authorization framework that moves away from long-lived credentials. It issues short-lived, operation-specific "permission coupons" that are verified before every action.

## Features
- **Short-Lived Coupons**: PASETO v4 tokens with short TTLs.
- **Proof-of-Possession (PoP)**: Coupons bound to mTLS client certificates.
- **Revocation**: Immediate revocation via Redis blacklist.
- **Audit Logging**: Immutable logs for every issuance and verification.
- **Policy Enforcement**: OPA-like policy checks for issuance.

## Architecture
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL (Audit Logs)
- **Cache**: Redis (Revocation)
- **Frontend**: React/TypeScript (Admin UI)
- **CLI**: Python-based command line tool

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (optional, for full stack)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/discproject.git
   cd discproject
   ```

2. **Backend Setup**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   ```

4. **CLI Setup**
   ```bash
   # CLI uses the SDK in sdk/
   pip install -r backend/requirements.txt # SDK deps are similar
   ```

### Running Locally

1. **Start Backend**
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   *Note: Requires Redis running on localhost:6379 or it will use an in-memory mock.*

2. **Start Frontend**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Use CLI**
   ```bash
   # Mint a coupon
   python cli/disc-cli.py mint --audience my-service --scope read:data

   # Verify a coupon
   python cli/disc-cli.py verify "v4.public..."
   ```

## Security
- **OIDC**: Pass `Authorization: Bearer <token>` header to `/issue`.
- **mTLS**: Pass `X-Client-Cert-Hash` header to bind coupon to a certificate.

## License
MIT
