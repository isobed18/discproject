import argparse
import json
import sys
import os

# Add project root to path to import sdk if not installed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sdk.disc_sdk import DiscClient

def main():
    parser = argparse.ArgumentParser(description="DISC CLI Tool")
    parser.add_argument("--url", default="http://localhost:8000/v1", help="API Base URL")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Mint
    mint_parser = subparsers.add_parser("mint", help="Mint a new coupon")
    mint_parser.add_argument("--audience", required=True, help="Target audience")
    mint_parser.add_argument("--scope", required=True, help="Permissions scope")
    mint_parser.add_argument("--ttl", type=int, default=300, help="Time to live in seconds")

    # Verify
    verify_parser = subparsers.add_parser("verify", help="Verify a coupon")
    verify_parser.add_argument("token", help="The coupon token")

    # Revoke
    revoke_parser = subparsers.add_parser("revoke", help="Revoke a coupon")
    revoke_parser.add_argument("jti", help="The JTI of the coupon")
    revoke_parser.add_argument("--reason", default="unspecified", help="Reason for revocation")

    args = parser.parse_args()
    
    client = DiscClient(base_url=args.url)

    try:
        if args.command == "mint":
            result = client.issue_coupon(args.audience, args.scope, args.ttl)
            print(json.dumps(result, indent=2))
        elif args.command == "verify":
            result = client.verify_coupon(args.token)
            print(json.dumps(result, indent=2))
        elif args.command == "revoke":
            result = client.revoke_coupon(args.jti, args.reason)
            print(json.dumps(result, indent=2))
        else:
            parser.print_help()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
