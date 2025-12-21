package disc.authz

import rego.v1

# Varsayılan: Her şeyi REDDET
default allow := false

# 1. ISSUE COUPON (Kupon Üretme)
allow if {
    input.path == "/issue"
    input.method == "POST"
    
    # --- DÜZELTME ---
    # Backend token'ı zaten doğruladı (verify_oidc_token).
    # OPA olarak sadece "Bu kullanıcı Anonim mi?" diye bakmamız yeterli.
    # Eğer "anonymous" değilse, geçerli bir token ile gelmiştir.
    input.token.sub != "anonymous"
}

# 2. VERIFY (Doğrulama) - Herkese açık
allow if {
    input.path == "/verify"
    input.method == "POST"
}

# 3. ADMIN İŞLEMLERİ (Audit Logs & Revoke)
# Burası sıkı kalmalı. Sadece 'admin' yetkisi olanlar girebilir.
allow if {
    is_admin_endpoint
    # Token scope içinde "admin" yazıyor mu?
    contains(input.token.scope, "admin")
}

# Yardımcı Kurallar
is_admin_endpoint if startswith(input.path, "/audit")
is_admin_endpoint if input.path == "/revoke"