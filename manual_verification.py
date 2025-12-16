import requests
import time

# DEĞİŞİKLİK 1: "localhost" yerine doğrudan IP "127.0.0.1" yazıyoruz.
# Bu, Windows'un IPv6 karmaşasını engeller.
BASE_URL = "http://127.0.0.1:8000/v1"

# DEĞİŞİKLİK 2: Tarayıcı gibi görünmek için Header
HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Content-Type': 'application/json'
}

def test_flow():
    # Proxy ayarlarını (varsa) görmezden gelmek için Session kullanıyoruz
    session = requests.Session()
    session.trust_env = False  # Bu satır sistemdeki Proxy/VPN ayarlarını atlar!

    print(f"--- Bağlantı deneniyor: {BASE_URL} ---")
    
    print("\n--- 1. Testing Delegation ---")
    d_payload = {"delegate": "anonymous", "resource": "secure-doc-1", "ttl": 3600}
    
    try:
        # session.post kullanıyoruz
        d_res = session.post(f"{BASE_URL}/delegations", json=d_payload, headers=HEADERS)
        print(f"Delegation Status: {d_res.status_code}")
        print(f"Response: {d_res.text}")
    except Exception as e:
        print(f"HATA OLUŞTU: {e}")
        print("İPUCU: Backend terminalinde '/v1/delegations' yolu tanımlı mı? '/docs' adresine girip kontrol edebilirsin.")
        return

    print("\n--- 2. Testing Issue Coupon ---")
    i_payload = {"audience": "app-srv", "scope": "read", "resource": "secure-doc-1"}
    try:
        i_res = session.post(f"{BASE_URL}/issue", json=i_payload, headers=HEADERS)
        print(f"Issue Status: {i_res.status_code}")
        if i_res.status_code == 200:
            print(f"Coupon: {i_res.json().get('coupon')}")
        else:
            print(f"Error Body: {i_res.text}")
    except Exception as e:
        print(f"Issue Hatası: {e}")

    print("\n--- 3. Testing Partial Evaluation ---")
    p_payload = {"resources": ["secure-doc-1", "forbidden-doc-99"], "action": "read", "audience": "app-srv"}
    try:
        p_res = session.post(f"{BASE_URL}/filter-authorized", json=p_payload, headers=HEADERS)
        print(f"Partial Eval Result: {p_res.json()}")
    except Exception as e:
        print(f"Partial Eval Hatası: {e}")

if __name__ == "__main__":
    test_flow()