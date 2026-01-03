
# PERSON C: GÖRSEL KANIT REHBERİ (QA VISUAL MAP)

> **Kritik Not:** Bu komutları `discproject_env` aktifken çalıştırın.

---

## 🟢 SORU 1: CLI İLE TOKEN ÜRETİMİ
**Soru:** "CLI ile bir kupon/token üretebiliyor ve sonra doğrulayabiliyor muyum?"
**Cevap:** "Evet. UI olmasa bile komut satırından her şeyi yapabiliyoruz."

**GÖSTERİLECEK YER (Terminal):**
1.  **Token Üretme:**
```powershell
python scripts/demo_cli.py issue --audience "mobil-app"
```
*(Ekranda "Token Issued" ve "JTI" kodunu gösterin. "Bu token şimdi dosyaya (last_token.txt) kaydedildi" diyebilirsiniz.)*

2.  **Token Doğrulama:**
```powershell
python scripts/demo_cli.py verify
```
*(Ekranda "✅ STATUS: VALID" ve Claims bilgisini gösterin.)*

---

## 🟢 SORU 2: GATEWAY GÜVENLİĞİ
**Soru:** "Gateway, doğru token yoksa isteği engelliyor mu?"
**Cevap:** "Evet. Gateway bir güvenlik kapısıdır. Tokensiz kimse geçemez."

**HAZIRLIK (Bir sekmeyi buna ayırın):**
```powershell
# Gateway'i 8081 portunda başlatın (Backend 8000'de çalışıyor olmalı)
$env:UPSTREAM_BASE_URL="http://localhost:8000"; python -m uvicorn gateway.main:app --port 8081
```

**KANIT (Başka Terminalden):**
1.  **Tokensiz İstek (Reddedilir):**
```powershell
# Gateway üzerinden korumalı bir kaynağa erişmeye çalışalım
curl.exe -v http://localhost:8081/v1/issue
```
*(Sonuç: `401 Unauthorized` veya `403 Forbidden` veya Gateway Plugin hatası. Önemli olan 200 dönmemesidir.)*

---

## 🟢 SORU 3: UI REVOCATION (İPTAL)
**Soru:** "Admin panelinden revoke (iptal) yapıp loglarda görebiliyor muyum?"
**Cevap:** "Evet. UI sadece görüntü değil, tam kontrol sağlar."

**GÖSTERİLECEK YER (Tarayıcı):**
1.  **Adres:** `http://localhost:5173` (Dashboard).
2.  **Menü:** "Revocation Ops" (veya Revoke sekmesi).
3.  **Aksiyon:**
    *   Soru 1'de ürettiğiniz JTI kodunu (veya `scripts/demo_cli.py issue` ile yeni üretip) "JTI" kutusuna yapıştırın.
    *   **Reason:** "Suspected abuse" seçin.
    *   **Revoke** butonuna basın.
    *   Sağ taraftaki veya alttaki "Recent Revocations" tablosunda yeni satırı gösterin.
    *   Daha sonra CLI'dan tekrar `verify` yaparak "INVALID" olduğunu da gösterebilirsiniz (Opsiyonel şov).
