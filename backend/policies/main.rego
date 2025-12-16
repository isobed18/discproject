package disc.authz

import rego.v1

# Default Deny: Everything is forbidden unless explicitly allowed.
default allow = false

# Main Allow Rule
allow if {
    # 1. Token must be valid (checked by backend, here we check attributes)
    input.audience == input.token.aud
    
    # 2. Check if user has the right scope OR has a delegation
    has_permission
}

# Rule: Has Permission via Direct Scope
has_permission if {
    # Check if the requested scope is in the user's token scope
    # Example: User has "read:data", requests "read:data"
    some scope in input.token.scope
    scope == input.scope
}

# Rule: Has Permission via Delegation (Week 3 Feature)
has_permission if {
    # Check if the user ID is in the delegation list for this resource
    # input.delegations is a dictionary: {"resource_id": ["user1", "user2"]}
    allowed_users := input.delegations[input.resource]
    input.token.sub in allowed_users
}

# Optional: Admin Override
has_permission if {
    "admin" in input.token.scope
}