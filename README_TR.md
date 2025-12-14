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

---

## 🛡️ OPA Politika Motoru Kurulumu (Önemli)

> [!IMPORTANT]
> **OPA Özelliği (Policy Engine) MVP'de eksikti.**
> Lütfen bundan sonra `main` branch'in bu versiyonunu kullanın. Tutarlılık için herkesin acilen `pull` etmesi gerekmektedir.

Proje artık yetkilendirme kararları için **Open Policy Agent (OPA)** kullanmaktadır.

### 1. OPA'yı Yerel Olarak Çalıştırma
Politikaları katı bir şekilde uygulamak için bir OPA sunucusu çalıştırmalısınız. En kolay yol Docker kullanmaktır:

```bash
docker run -p 8181:8181 openpolicyagent/opa:latest-static run --server --addr :8181
```

### 2. Politikaları Yükleme
OPA çalıştıktan sonra, Rego politikasını yükleyin:

**Bash / Command Prompt (cmd.exe):**
```bash
curl -X PUT --data-binary @backend/policies/main.rego http://localhost:8181/v1/policies/disc/authz
```

**PowerShell (Windows):**
PowerShell'de `curl` komutu farklı çalışır. Git Bash yüklüyse `curl.exe` kullanın veya şu komutu çalıştırın:
```powershell
Invoke-RestMethod -Method PUT -Uri "http://localhost:8181/v1/policies/disc/authz" -Body (Get-Content backend/policies/main.rego -Raw)
```

### 3. Geliştirici Modunu (Dev Mode) Kapatma
Varsayılan olarak backend `DEV_MODE=True` ile çalışır. Bu mod, OPA kapalı olsa bile isteklere **izin verir** (Fail-Open), böylece geliştirme süreci bloklanmaz.
Gerçek denetimi test etmek için:
1.  `backend/core/config.py` dosyasını açın.
2.  `DEV_MODE = False` yapın.
3.  Backend'i yeniden başlatın.

Artık OPA çalışmıyorsa veya politika erişimi reddediyorsa, istekleriniz reddedilecektir (403 Forbidden).

---

## 🧪 Yeni Özelliklerin Test Edilmesi (3. Hafta)

**Delegasyon** ve **Kısmi Değerlendirme (Partial Eval)** özelliklerini test etmek için aşağıdaki adımları izleyin.

## 🧪 Yeni Özelliklerin Test Edilmesi (3. Hafta - Üretim Senaryosu)

**Delegasyon** ve **Kısmi Değerlendirme** özelliklerini gerçekçi bir şekilde (Üretim ortamına uygun) test etmek için **Kimlik Doğrulama Tokenları (OIDC)** kullanmalıyız.

### Ön Hazırlık (Token Üretme)
Lokal geliştirmede gerçek bir Identity Provider (IdP) olmadığı için, test amaçlı geçerli bir token üretmemiz gerekir. Bunun için bir yardımcı script hazırladık:

```bash
# "ali" kullanıcısı için token üret
python cli/create_test_token.py ali
# Çıktı örneği: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```
*Bu tokenı PowerShell'de bir değişkene atayın.*

### 1. Delegasyon (Yetki Devri)
"ali" kullanıcısına erişim verin.

**PowerShell:**
```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/v1/delegations" `
     -ContentType "application/json" `
     -Body '{"delegate": "ali", "resource": "secure-doc-1", "ttl": 3600}'
```

### 2. Toplu Kontrol (Token Kullanarak)
Şimdi, sanki gerçekten **"ali"** giriş yapmış gibi tokenını kullanarak istek atalım.

**PowerShell:**
```powershell
# 1. Tokenı al
$Token = python cli/create_test_token.py ali

# 2. Token ile istek at
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/v1/filter-authorized" `
     -Headers @{Authorization=("Bearer " + $Token)} `
     -ContentType "application/json" `
     -Body '{"resources": ["secure-doc-1", "forbidden-doc-99"], "action": "read", "audience": "app-srv"}'
```
*Sonuç:* OPA, tokenın "ali"ye ait olduğunu görür, "ali"nin delegasyonu olduğunu doğrular ve `["secure-doc-1"]` cevabını verir.

### 3. Kupon Alma (Token Kullanarak)
Aynı şekilde, kaynak için PASETO kuponu isteyelim.

**PowerShell:**
```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/v1/issue" `
     -Headers @{Authorization=("Bearer " + $Token)} `
     -ContentType "application/json" `
     -Body '{"audience": "app-srv", "scope": "read", "resource": "secure-doc-1"}'
```

---

## 📖 Kullanım Kılavuzu
Varsayılan olarak backend `DEV_MODE=True` ile çalışır. Bu mod, OPA kapalı olsa bile isteklere **izin verir** (Fail-Open), böylece geliştirme süreci bloklanmaz.
Gerçek denetimi test etmek için:
1.  `backend/core/config.py` dosyasını açın.
2.  `DEV_MODE = False` yapın.
3.  Backend'i yeniden başlatın.

Artık OPA çalışmıyorsa veya politika erişimi reddediyorsa, istekleriniz reddedilecektir (403 Forbidden).

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
4.  **Politika Uygulama (OPA)**:
    *   Ayrıntılı yetkilendirme mantığı için **Open Policy Agent** entegrasyonu.
    *   **Delegasyon Kuralları**: Rego politikaları aracılığıyla yetki devrini (Örn: Kullanıcı A, belirli kaynaklar için Kullanıcı B adına işlem yapabilir) destekler.
    *   **Geliştirici Modu (Dev Mode)**: OPA olmadan yerel geliştirme için hataya dayanıklı (fail-open) çalışma modu.

## 📊 Observability & Operasyonel Olgunluk (Week 4)

Bu proje, yalnızca fonksiyonel çalışmayı değil, üretim ortamına yakın operasyonel davranışı hedefler.  
Week 4 kapsamında sistem operasyonel olgunluk (operational maturity) seviyesine taşınmıştır.

---

### 🔍 Metrikler (Prometheus)

Backend, Prometheus uyumlu metrikleri aşağıdaki endpoint üzerinden sunar:

* **GET /metrics**

Toplanan temel metrikler:

* **disc_coupon_issue_total** — üretilen kupon sayısı
* **disc_issue_latency_seconds** — kupon üretim gecikmesi
* **disc_revoke_total** — iptal edilen kupon sayısı
* **disc_policy_deny_total** — OPA tarafından reddedilen istekler

---

### 📈 Grafana Dashboard Örnekleri

* **Kupon Üretim Hızı (Issue Rate)**

```
rate(disc_coupon_issue_total[1m])
```

* **p95 Gecikme (Latency)**

```
histogram_quantile(
  0.95,
  sum(rate(disc_issue_latency_seconds_bucket[5m])) by (le)
)
```

* **Revocation Freshness (İptal Güncelliği)**

```
time() - disc_last_revoke_timestamp
```

Bu paneller, sistemin yük altında davranışını, yetkilendirme gecikmelerini ve iptal mekanizmasının tutarlılığını gözlemlemeyi sağlar.

---

### 🛡️ Fail-Closed Güvenlik Davranışı

Sistem, yetkilendirme kararları için harici **Open Policy Agent (OPA)** kullandığından aşağıdaki güvenlik davranışlarını sergiler:

* OPA erişilebilir değilse → **/v1/issue → 503 Service Unavailable**
* OPA erişilebilir fakat politika reddederse → **403 Forbidden**
* **DEV_MODE = False** iken varsayılan davranış **fail-closed**’dır

Bu yaklaşım, yanlışlıkla yetki verilmesini engeller ve **secure-by-default** ilkesini uygular.
