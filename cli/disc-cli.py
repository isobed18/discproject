import argparse
import json
import sys
from datetime import datetime, timedelta

# Mock implementation for prototype
def mint_coupon(audience, scope, ttl):
    print(f"Minting coupon for audience={audience}, scope={scope}, ttl={ttl}")
    # In real impl, this would call the API
    mock_coupon = {
        "iss": "disc-ca",
        "aud": audience,
        "scope": scope,
        "exp": (datetime.utcnow() + timedelta(seconds=int(ttl))).isoformat() + "Z",
        "jti": "mock-uuid-1234"
    }
    return "v4.public.mock_signature." + json.dumps(mock_coupon)

def decode_coupon(token):
    print(f"Decoding token: {token}")
    # In real impl, this would verify signature
    try:
        payload_part = token.split(".")[2]
        return json.loads(payload_part)
    except:
        return {"error": "Invalid token format"}

def validate_coupon(token):
    print(f"Validating token: {token}")
    # In real impl, this would call /verify endpoint
    return True

def main():
    parser = argparse.ArgumentParser(description="DISC CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Mint
    mint_parser = subparsers.add_parser("mint", help="Mint a new coupon")
    mint_parser.add_argument("--audience", required=True, help="Target audience")
    mint_parser.add_argument("--scope", required=True, help="Permissions scope")
    mint_parser.add_argument("--ttl", default=300, help="Time to live in seconds")

    # Decode
    decode_parser = subparsers.add_parser("decode", help="Decode a coupon")
    decode_parser.add_argument("token", help="The coupon token")

    # Validate
    validate_parser = subparsers.add_parser("validate", help="Validate a coupon")
    validate_parser.add_argument("token", help="The coupon token")

    args = parser.parse_args()

    if args.command == "mint":
        token = mint_coupon(args.audience, args.scope, args.ttl)
        print(f"Generated Coupon: {token}")
    elif args.command == "decode":
        payload = decode_coupon(args.token)
        print(json.dumps(payload, indent=2))
    elif args.command == "validate":
        is_valid = validate_coupon(args.token)
        print(f"Valid: {is_valid}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
