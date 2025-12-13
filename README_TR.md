# DISC (Dijital Kimlik Diski & Kısa Ömürlü Yetenek Kuponları)

DISC, uzun ömürlü ve statik kimlik bilgilerinden (API Anahtarları veya uzun ömürlü JWT'ler gibi) uzaklaşmak için tasarlanmış yeni nesil bir yetkilendirme çerçevesidir. Bunun yerine, her işlemden önce kriptografik olarak imzalanan ve doğrulanan **kısa ömürlü, operasyona özel "izin kuponları"** verir.

Bu proje, bu kuponları vermek, doğrulamak ve iptal etmekten sorumlu merkezi hizmet olan **Kupon Otoritesi (Coupon Authority - CA)**'ni uygular.

---

## 🏗️ Mimari ve Bileşenler

Proje, birlikte çalışan birkaç temel bileşenden oluşur:

1.  **Backend (Kupon Otoritesi Çekirdeği)**:
    *   **Python FastAPI** ile geliştirilmiştir.
    *   Kriptografik imzalama (PASETO v4) ve doğrulama işlemlerini yönetir.
    *   Kupon vermeden önce politikaları (OPA tarzı) uygular.
    *   İptal listesini (Redis) ve denetim günlüklerini (Audit Logs) yönetir.

2.  **Frontend (Yönetici Paneli)**:
    *   **React & TypeScript** ile geliştirilmiştir.
    *   Yöneticilerin denetim günlüklerini görmesini ve kuponları manuel olarak iptal etmesini sağlayan bir panel sunar.

3.  **CLI (Komut Satırı Aracı)**:
    *   Geliştiricilerin ve CI/CD süreçlerinin CA ile etkileşime girmesi (Kupon Oluşturma, Doğrulama, İptal Etme) için Python tabanlı bir araçtır.

4.  **SDK (Yazılım Geliştirme Kiti)**:
    *   DISC'i diğer uygulamalara entegre etmeyi kolaylaştıran bir Python kütüphanesidir (`disc_sdk`).

---

## 📂 Proje Yapısı ve Dosyalar

Yeni katkıda bulunacaklar için kod tabanının detaylı dökümü:

*   **`backend/`**: Çekirdek API sunucusu.
    *   `main.py`: Uygulamanın giriş noktasıdır. API'yi ve CORS ayarlarını başlatır.
    *   `api/`: REST API tanımlarını içerir.
        *   `endpoints.py`: `/issue`, `/verify`, `/revoke` gibi uç noktaları (route) tanımlar.
        *   `models.py`: İstek ve cevapların veri modellerini (Pydantic şemaları) tanımlar.
    *   `core/`: Temel mantık ve konfigürasyon.
        *   `security.py`: PASETO v4 imzalama/doğrulama, Anahtar yönetimi, OIDC token çözme ve mTLS başlıklarını okuma işlemlerini yapar.
        *   `config.py`: Ortam değişkenlerini (Redis URL, Gizli Anahtarlar) yükler.
    *   `services/`: İş mantığı servisleri.
        *   `revocation.py`: İptal edilen tokenları kontrol etmek için Redis ile iletişimi yönetir.
*   **`frontend/`**: Yönetici Arayüzü.
    *   `src/App.tsx`: Logları çekme ve token iptal etme mantığını içeren ana React bileşeni.
*   **`cli/`**:
    *   `disc-cli.py`: CLI komutlarını çalıştıran betik. Arka planda SDK'yı kullanır.
*   **`sdk/`**:
    *   `disc_sdk/client.py`: Backend'e HTTP istekleri atmayı kolaylaştıran Python istemci kütüphanesi.
*   **`docs/`**: Dokümantasyon dosyaları (Güvenlik, Yedekleme stratejileri).

---

## 🚀 Başlangıç Rehberi

### Gereksinimler
*   **Python 3.11+**
*   **Node.js 18+**
*   **Redis** (Yerel geliştirme için isteğe bağlıdır, Redis yoksa sistem otomatik olarak bellek içi (in-memory) moda geçer).

### Kurulum

1.  **Depoyu klonlayın**:
    ```bash
    git clone https://github.com/isobed18/discproject.git
    cd discproject
    ```

2.  **Backend Kurulumu**:
    ```bash
    cd backend
    pip install -r requirements.txt
    ```

3.  **Frontend Kurulumu**:
    ```bash
    cd frontend
    npm install
    ```

### Projeyi Çalıştırma

1.  **Backend'i Başlatın**:
    ```bash
    # Ana dizinden (discproject klasöründen)
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
    ```
    API şu adreste çalışacaktır: `http://localhost:8000`.

2.  **Frontend'i Başlatın**:
    ```bash
    # frontend dizininden
    cd frontend
    npm run dev
    ```
    Arayüz şu adreste çalışacaktır: `http://localhost:5173`.

---

## 📖 Kullanım Kılavuzu

### 1. CLI Kullanımı
Sistemi test etmenin en kolay yolu CLI aracıdır.

*   **Kupon Oluşturma (Mint)**:
    Belirli bir kitle (audience) ve yetki (scope) için yeni kupon oluşturur.
    ```bash
    python cli/disc-cli.py mint --audience my-service --scope read:data --ttl 300
    ```
    *Dönüş*: İmzalı `coupon` metnini içeren bir JSON çıktısı.

*   **Kupon Doğrulama (Verify)**:
    Kuponun geçerli, süresi dolmamış ve iptal edilmemiş olduğunu kontrol eder.
    ```bash
    python cli/disc-cli.py verify "v4.public.KUPON_METNI..."
    ```

*   **Kupon İptal Etme (Revoke)**:
    Bir kuponu JTI (ID) numarasını kullanarak geçersiz kılar.
    ```bash
    python cli/disc-cli.py revoke "KUPON_JTI_UUID"
    ```

### 2. API Uç Noktaları (Endpoints)

*   **`POST /v1/issue`**
    *   **Amaç**: Yeni bir PASETO kuponu verir.
    *   **Başlıklar (Headers)**:
        *   `Authorization`: Bearer <OIDC_TOKEN> (İsteğe bağlı, isteği yapanı tanımlar).
        *   `X-Client-Cert-Hash`: <SHA256> (İsteğe bağlı, kuponu bir mTLS sertifikasına bağlar).
    *   **Gövde (Body)**:
        ```json
        {
          "audience": "target-service",
          "scope": "read:data",
          "ttl_seconds": 300
        }
        ```

*   **`POST /v1/verify`**
    *   **Amaç**: Bir kuponu doğrular.
    *   **Gövde**: `{"coupon": "v4.public..."}`
    *   **Cevap**: Geçerliyse kupon içeriğini (claims), değilse hata döner.

*   **`POST /v1/revoke`**
    *   **Amaç**: Bir kuponu iptal eder.
    *   **Gövde**: `{"jti": "uuid...", "reason": "compromised"}`

*   **`GET /v1/audit-logs`**
    *   **Amaç**: Tüm kupon verme ve iptal etme olaylarının listesini döner.

---

## 🔒 Uygulanan Güvenlik Özellikleri

1.  **PASETO v4 (Public)**: İmzalama için Asimetrik Ed25519 anahtarları kullanıyoruz. Bu, sadece CA'nın kupon verebileceği, ancak herkesin (public key ile) doğrulayabileceği anlamına gelir.
2.  **Sahiplik Kanıtı (PoP)**: Eğer kupon verilirken `X-Client-Cert-Hash` başlığı varsa, bu bilgi token içine (`cnf` claim) gömülür. Token'ı alan servis, token'ı sunan istemcinin bu sertifika hash'ine sahip olup olmadığını kontrol etmelidir.
3.  **OIDC Entegrasyonu**: Sistem, kupon isteyen kişinin kimliğini doğrulamak için standart OIDC tokenlarını (Auth0, Keycloak vb.) kabul eder.
4.  **Politika Uygulama**: Kupon verilmeden önce kurallar kontrol edilir (Örn: "Sadece internal-admin kullanıcısı admin yetkisi isteyebilir").
