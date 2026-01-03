# PERSON D: GÖRSEL KANIT REHBERİ (QA VISUAL MAP)

> **Kritik Not:** Bu komutları `discproject_env` aktifken çalıştırın.

---

## 🟢 HAFTA 1: STRATEJİK TEMEL (STRIDE & OPA)
**Soru:** "Tehdit modelini nasıl koda döktün?" (403 Forbidden Gösterimi)

**GÖSTERİLECEK YER:**
1.  **VS Code:** `backend/policies/main.rego` -> `default allow = false` (Satır 5).
2.  **Açıklama:** "Tehdit analizinde 'yetki yükseltme' riskini gördük. Bu yüzden varsayılan olarak her şeyi yasakladık."

**DEMO KOMUTU (Yetkisiz Erişim):**
```powershell
# Geçerli bir body ama yetkisiz (Token yok) istek atarak 403 Forbidden alın
curl.exe -v -X POST http://localhost:8000/v1/issue `
  -H "Content-Type: application/json" `
  -d '{\"audience\": \"test\", \"scope\": \"read\", \"ttl_seconds\": 300}'
```
*(Ekranda `< HTTP/1.1 403 Forbidden` görmelisiniz. Bu, "Veri düzgün ama senin yetkin yok" demektir.)*

---

## 🟢 HAFTA 2: IMMUTABLE LOGS (CANLI İZLEME)
**Soru:** "Logların güvenilir olduğunu nasıl kanıtlıyorsun?"

**GÖSTERİLECEK YER:**
1.  **Terminal:** Canlı izleme scripti.
2.  **Açıklama:** "Her log Kafka'ya gitmeden önce kriptografik olarak imzalanıyor. İşte canlı kanıtı."

**DEMO KOMUTU (Packet Sniffer):**
```powershell
python backend/monitor_live.py
```
*(Bu çalışırken başka bir terminalden `python scripts/demo_mint.py` çalıştırıp akan şifreli veriyi gösterin.)*

---

## 🟢 HAFTA 3: DELEGASYON & PERFORMANS
**Soru:** "Performans düşmeden yetki devri nasıl oluyor?"

**GÖSTERİLECEK YER:**
1.  **VS Code:** `backend/api/endpoints.py` -> `create_delegation` fonksiyonu.
2.  **Dashboard:** Traceability sayfasındaki "Latency" grafiği.
3.  **Açıklama:** "OPA'nın yükünü hafifletmek için Redis tabanlı Partial Evaluation kullanıyoruz. Kod burada, sonuç dashboard'da."

---

## 🟢 HAFTA 4: VERİ KORUMA (ENCRYPTION & RBAC)
**Soru:** "Hassas veriler (PII) nasıl korunuyor?"

**GÖSTERİLECEK YER:**
1.  **Terminal (Monitor çıktısı):** `monitor_live.py` ekranında `details` kısmına bakın.
2.  **Açıklama:** "Veritabanına giden veri bu. `email: enc:xxx` şeklinde şifreli. Ben bile okuyamam."
3.  **Aksiyon:** `scripts/demo_mint.py` çalıştırıp başarılı bir işlem yapın, ama logda verinin şifreli olduğunu vurgulayın.

**DEMO KOMUTU:**
```powershell
python scripts/demo_mint.py
```

---

## 🟢 HAFTA 5: SERTLEŞTİRME (RATE LIMITING)
**Soru:** "Saldırı anında sistem ne yapıyor?" (429 Too Many Requests)

**GÖSTERİLECEK YER:**
1.  **Terminal:** Spam saldırısı simülasyonu.
2.  **VS Code (Opsiyonel):** `docs/incident_playbook.md` (Incident Planı).
3.  **Açıklama:** "Rate Limiter 5. istekten sonra kapıyı kapatıyor. İzleyin."

**DEMO KOMUTU (Saldırı Başlat):**
```powershell
# Arka arkaya 10 geçerli istek atarak sistemi kilitleme
1..10 | ForEach-Object { 
    curl.exe -s -o /dev/null -w "%{http_code} " -X POST http://localhost:8000/v1/issue `
    -d '{\"audience\": \"test\", \"scope\": \"read\", \"ttl_seconds\": 300}' `
    -H "Content-Type: application/json" 
}
```
*(Çıktıda: `200 200 200 200 200 429 429 429...` görmelisiniz.)*
