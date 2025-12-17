package disc.authz

import rego.v1

# Varsayılan: REDDET (Modern atama operatörü := kullanılır)
default allow := false

# --- MODERN KURAL ---
allow if {
    # 1. Audience Kontrolü
    input.audience == input.token.aud

    # 2. Scope Kontrolü
    input.scope == input.token.scope

    # 3. Delegasyon Kontrolü
    # Kaynak için yetkili listeyi al
    user_list := input.delegations[input.resource]
    
    # Kullanıcı (token.sub) bu listenin içinde mi? ('in' operatörü modern OPA'da daha temizdir)
    input.token.sub in user_list
}