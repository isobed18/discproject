# 3. Hafta Sistemi: Detaylı Akış ve Mimari (Türkçe)

Bu doküman, 3. Hafta kapsamında geliştirilen **Güvenlik ve Politika Motoru** altyapısının nasıl çalıştığını, bileşenlerin görevlerini ve veri akışını açıklar.

---

## 🏗️ 1. Mimari Bileşenler

Sistem 3 ana parçadan oluşur:

1.  **FastAPI Backend (Bizim Kodumuz):** İstemciden (Client) gelen istekleri karşılar. "Yetki var mı?" diye OPA'ya sorar. Eğer "Evet" cevabı alırsa işlemi yapar.
2.  **Redis (Hafıza):** Geçici verileri tutar. Özellikle **Delegasyon (Yetki Devri)** bilgilerini burada saklarız. "Ali, Veli'ye 1 saatliğine izin verdi" gibi bilgileri tutar.
3.  **Docker & OPA (Open Policy Agent):**
    *   **Neden Docker?** OPA, Go diliyle yazılmış bağımsız bir sunucudur. Bilgisayarınıza tek tek kurmak yerine, Docker ile izole bir "konteyner" (sanal kutu) içinde çalıştırıyoruz. Bu sayede `docker run` diyerek her yerde (Windows, Linux, Mac) aynı şekilde çalışmasını garantiliyoruz.
    *   **Görevi:** OPA, sistemin **Yargıcıdır**. Karar verir. Backend ona "Ali bu dosyayı okuyabilir mi?" diye verileri gönderir, OPA da kurallara (Rego dosyasına) bakıp "True/False" (Evet/Hayır) döner.

---

## 🔄 2. Veri Akışı ve Parametreler

Bir kullanıcının sisteme erişip işlem yapması sırasıyla şöyle gerçekleşir:

### Adım 1: Kimlik (Token)
Kullanıcı önce kim olduğunu kanıtlamalıdır.
*   **OIDC Token:** Google veya Auth0 gibi bir yerden alınan kimlik kartıdır. Biz testte `create_test_token.py` ile sahte bir kart üretiyoruz. Bu kartta `sub: ali` (Adı Ali) yazar.

### Adım 2: İstek Atma (Endpoint Parametreleri)
Kullanıcı `/issue` (Kupon İste) endpointine gelir. Şu bilgileri gönderir:
*   **`audience` (Hedef):** "Ben bu yetkiyi nerede kullanacağım?" (Örn: `app-srv` yani Ana Uygulama Sunucusu).
*   **`scope` (Kapsam):** "Ne yapmak istiyorum?" (Örn: `read`, `write`, `admin`).
*   **`resource` (Kaynak):** "Hangi dosya üzerinde?" (Örn: `secure-doc-1`).

### Adım 3: Backend ve OPA Konuşması
Backend isteği alır. Hemen **Redis**'e bakar: "Bu dosya için birisine yetki verilmiş mi?". Bulduğu delegasyonları ve kullanıcının bilgilerini paketleyip OPA'ya gönderir:

```json
// OPA'ya giden paket (Input)
{
  "token": { "sub": "ali", "scope": "default" }, // İsteyen kişi
  "action": "read",                              // Yapmak istediği
  "resource": "secure-doc-1",                    // Hedef dosya
  "delegations": { "secure-doc-1": ["ali"] }     // Redis'ten gelen bilgi: "ali'ye izin verilmiş"
}
```

### Adım 4: OPA Kararı (Rego)
OPA'daki `main.rego` kuralları çalışır. Mantık şöyledir:
1.  **Admin mi?** (Hayır)
2.  **Dosyanın Sahibi mi?** (Hayır)
3.  **Delegasyon Var mı?** BAKAR -> Evet, `delegations` listesinde "ali" var!
4.  **SONUÇ:** `allow = true` (İzin Ver).

### Adım 5: Kupon Üretimi (PASETO)
OPA "Tamam" dedikten sonra, Backend son bir "Geçiş Bileti" üretir. Buna **PASETO Coupon** diyoruz.
*   **Neden?** Kullanıcı her işlemde OPA'ya tekrar tekrar sorulmasın diye, eline süreli (örn. 5 dakika) imzalı bir bilet verilir.
*   Bu bileti (Kuponu) alan kullanıcı, artık dosyayı indirmek için Dosya Sunucusuna gittiğinde sadece bu bileti gösterir. "Bak Backend bana izin verdi, imzasını kontrol et" der.

---

## ❓ Neden Pushlamalıyız? (Git Stratejisi)

**Soru:** *Bu değişiklikleri main branch'e pushlamalı mıyız?*

**Cevap: KESİNLİKLE EVET.**

Sebepleri:
1.  **Temel Altyapı:** OPA ve Security (Person D), projenin "Güvenlik Duvarı"dır. Diğer arkadaşlar (Person A, B) yeni özellikler eklerken bu güvenlik duvarının arkasında çalışmalıdır.
2.  **Entegrasyon Sorunu:** Eğer siz bunu şimdi merge etmezseniz, diğerleri eski kod (güvenliksiz) üzerine kod yazar. İleride birleştirmek istediğinizde "Conflicts" (Çakışmalar) çok büyük olur.
3.  **Bloklayıcı Değil, Koruyucu:** Yaptığımız değişiklikler sistemi bozmuyor, sadece *izinsiz girişleri* engelliyor. `Fail-Closed` (Varsayılan Yasak) modunda olduğu için, diğer geliştiriciler de kendi testlerinde "Token alarak" işlem yapmayı öğrenmelidir. Bu da projenin kalitesini artırır.

**Öneri:**
Branch'inizi (`feature/week3-delegation-system`) hemen `main`'e merge edin. Diğer takım üyelerine de "Güvenlik altyapısı geldi, lütfen pull yapın" deyin. 🚀
