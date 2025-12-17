import requests
import time

BASE_URL = "http://localhost:8000/v1"

def test_full_scenario():
    print("🎬 SENARYO BAŞLIYOR: Delegasyon ve Yetkilendirme Testi\n")

    # 1. ADIM: Delegasyon Ekleme (Week 3)
    # "anonymous" kullanıcısına "wallet-123" kaynağı için yetki (delegation) tanımlıyoruz.
    # Normalde bunu kaynağın sahibi yapar, MVP'de herkes yapabiliyor.
    print("👉 1. Yetki Veriliyor (Delegation)...")
    delegation_payload = {
        "delegate": "anonymous",
        "resource": "wallet-123",
        "ttl": 3600
    }
    
    try:
        # Önce yetki verelim
        del_response = requests.post(f"{BASE_URL}/delegations", json=delegation_payload)
        
        if del_response.status_code == 200:
            print(f"✅ Yetki Başarıyla Verildi: {del_response.json()}")
        else:
            print(f"❌ Delegasyon Hatası: {del_response.status_code} - {del_response.text}")
            return

    except Exception as e:
        print(f"Bağlantı hatası (Delegasyon): {e}")
        return

    # 2. ADIM: Kupon İsteme (Week 4 - Audit Log & OPA Check)
    # Artık yetkimiz var (Redis'e yazıldı), OPA kontrol ettiğinde izin vermeli.
    print("\n👉 2. Kupon İsteniyor (Issuance)...")
    issue_payload = {
        "audience": "payment-service",
        "scope": "read:transactions",
        "resource": "wallet-123", # Delegasyon kontrolü bu kaynak için yapılacak
        "ttl_seconds": 300
    }
    
    try:
        issue_response = requests.post(f"{BASE_URL}/issue", json=issue_payload)
        
        if issue_response.status_code == 200:
            data = issue_response.json()
            print("✅ BAŞARILI: Kupon Alındı! 🎉")
            print(f"🎟️  Kupon JTI: {data.get('jti')}")
            print("\n👀 ŞİMDİ KAFKA TERMİNALİNE BAK! Şifreli log düşmüş olmalı.")
        else:
            print(f"❌ HATA: {issue_response.status_code}")
            print(issue_response.text)

    except Exception as e:
        print(f"Bağlantı hatası (Issue): {e}")

if __name__ == "__main__":
    test_full_scenario()