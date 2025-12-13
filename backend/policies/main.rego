package disc.authz

import rego.v1

# Default deny
default allow = false

# Allow if the user has the required audience and scope
allow if {
    input.audience == input.token.aud
    has_valid_scope
    has_valid_audience_role
}

# 1. Scope Check
# Simple check: Does the requested scope exist in the token's scope list?
# (In reality, scope might be "read:data" and we check split strings)
has_valid_scope if {
    # Check if the requested scope is contained in the token scopes
    # Input scope: "read:data"
    # Token scope: "read:data write:data"
    contains(input.token.scope, input.scope)
}

# 2. Role/Audience Constraints
# "admin" scope requires "internal-admin" audience
has_valid_audience_role if {
    not is_admin_request
}

has_valid_audience_role if {
    is_admin_request
    input.audience == "internal-admin"
}

is_admin_request if {
    contains(input.scope, "admin")
}

# 3. Delegation Rules (Week 3 Feature)
# Allow if a valid delegation exists for this user/resource
# Input: { "delegations": { "resource_id": ["user_a", "user_b"] } }
# This mocks a lookup. In real life, OPA might pull this from data.json or HTTP bundle.
allow if {
    some resource_id
    input.resource == resource_id
    allowed_users := input.delegations[resource_id]
    input.token.sub in allowed_users
}
