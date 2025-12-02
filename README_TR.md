# DISC (Dijital Kimlik Diski & Kısa Ömürlü Yetenek Kuponları)

DISC, uzun ömürlü kimlik bilgilerinden uzaklaşan, güvenli ve denetlenebilir bir yetkilendirme çerçevesidir. Her işlemden önce doğrulanan, kısa ömürlü ve operasyona özel "izin kuponları" verir.

## Özellikler
- **Kısa Ömürlü Kuponlar**: Kısa TTL süresine sahip PASETO v4 tokenları.
- **Sahiplik Kanıtı (PoP)**: mTLS istemci sertifikalarına bağlı kuponlar.
- **İptal (Revocation)**: Redis kara listesi üzerinden anında iptal.
- **Denetim Günlükleri (Audit Logging)**: Her veriliş ve doğrulama için değiştirilemez günlükler.
- **Politika Uygulama**: Veriliş için OPA benzeri politika kontrolleri.

## Mimari
- **Backend**: FastAPI (Python)
- **Veritabanı**: PostgreSQL (Denetim Günlükleri)
- **Önbellek**: Redis (İptal Listesi)
- **Frontend**: React/TypeScript (Yönetici Arayüzü)
- **CLI**: Python tabanlı komut satırı aracı

## Başlangıç

### Gereksinimler
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (isteğe bağlı, tam yığın için)

### Kurulum

1. **Depoyu klonlayın**
   ```bash
   git clone https://github.com/your-org/discproject.git
   cd discproject
   ```

2. **Backend Kurulumu**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Frontend Kurulumu**
   ```bash
   cd frontend
   npm install
   ```

4. **CLI Kurulumu**
   ```bash
   # CLI, sdk/ dizinindeki SDK'yı kullanır
   pip install -r backend/requirements.txt
   ```

### Yerel Çalıştırma

1. **Backend'i Başlatın**
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   *Not: localhost:6379 üzerinde Redis çalışmıyorsa bellek içi (in-memory) mock kullanılır.*

2. **Frontend'i Başlatın**
   ```bash
   cd frontend
   npm run dev
   ```

3. **CLI Kullanımı**
   ```bash
   # Kupon oluşturma (Mint)
   python cli/disc-cli.py mint --audience my-service --scope read:data

   # Kupon doğrulama (Verify)
   python cli/disc-cli.py verify "v4.public..."
   ```

## Güvenlik
- **OIDC**: `/issue` uç noktasına `Authorization: Bearer <token>` başlığı ile istek yapın.
- **mTLS**: Kuponu bir sertifikaya bağlamak için `X-Client-Cert-Hash` başlığını gönderin.

## Lisans
MIT
