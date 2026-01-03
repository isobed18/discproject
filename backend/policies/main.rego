package disc.authz

import rego.v1

# Varsayilan: Her seyi REDDET
default allow := false

# 1. ISSUE COUPON (Kupon Uretme)
allow if {
    input.path == "/issue"
    input.method == "POST"
    
    # --- DUZELTME ---
    # Backend token'i zaten dogruladi (verify_oidc_token).
    # OPA olarak sadece "Bu kullanici Anonim mi?" diye bakmamiz yeterli.
    input.token.sub != "anonymous"
}

# 2. VERIFY (Dogrulama) - Herkese acik
allow if {
    input.path == "/verify"
    input.method == "POST"
}

# 3. ADMIN ISLEMLERI (Audit Logs & Revoke)
# Burasi siki kalmali. Sadece 'admin' yetkisi olanlar girebilir.
allow if {
    is_admin_endpoint
    # Token scope icinde "admin" yaziyor mu?
    contains(input.token.scope, "admin")
}

# Yardimci Kurallar
is_admin_endpoint if startswith(input.path, "/audit")
is_admin_endpoint if input.path == "/revoke"