import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Add project root to path to import sdk if not installed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sdk.disc_sdk import DiscClient, FileStorage, InMemoryStorage, NullStorage


def _configure_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")
    if debug:
        # Make httpx / SDK chatty only in debug mode.
        logging.getLogger("httpx").setLevel(logging.DEBUG)
        logging.getLogger("disc_sdk").setLevel(logging.DEBUG)

def main():
    parser = argparse.ArgumentParser(description="DISC CLI Tool")
    parser.add_argument("--url", default=os.getenv("DISC_URL", "http://localhost:8000/v1"), help="API Base URL")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--timeout", type=float, default=float(os.getenv("DISC_TIMEOUT", "10")), help="HTTP timeout (seconds)")
    parser.add_argument("--retries", type=int, default=int(os.getenv("DISC_RETRIES", "3")), help="Max retries")
    parser.add_argument("--backoff", type=float, default=float(os.getenv("DISC_BACKOFF", "0.5")), help="Backoff factor")
    parser.add_argument("--offline", action="store_true", help="Enable offline mode (uses cache or local verification)")
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print minimal output (mint: coupon only, verify: true/false)",
    )
    parser.add_argument(
        "--offline-strategy",
        choices=["cache", "local", "auto", "none"],
        default=os.getenv("DISC_OFFLINE_STRATEGY", "cache"),
        help="Offline strategy for verify (default: cache)",
    )
    parser.add_argument(
        "--cache",
        choices=["memory", "file", "none"],
        default=os.getenv("DISC_CACHE", "file"),
        help="Cache backend (default: file)",
    )
    parser.add_argument(
        "--cache-path",
        default=os.getenv("DISC_CACHE_PATH", str(Path("~/.disc/cache.json").expanduser())),
        help="Cache file path (only used when --cache=file)",
    )
    parser.add_argument(
        "--public-key",
        default=os.getenv("DISC_PUBLIC_KEY_PEM", ""),
        help="Public key PEM (or path to PEM) for local/offline verification",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Mint
    mint_parser = subparsers.add_parser("mint", help="Mint a new coupon")
    mint_parser.add_argument("--audience", required=True, help="Target audience")
    mint_parser.add_argument("--scope", required=True, help="Permissions scope")
    mint_parser.add_argument("--ttl", type=int, default=300, help="Time to live in seconds")

    # Verify
    verify_parser = subparsers.add_parser("verify", help="Verify a coupon")
    verify_parser.add_argument("token", help="The coupon token")

    # Validate (alias for verify)
    validate_parser = subparsers.add_parser("validate", help="Validate a coupon (alias for verify)")
    validate_parser.add_argument("token", help="The coupon token")

    # Revoke
    revoke_parser = subparsers.add_parser("revoke", help="Revoke a coupon")
    revoke_parser.add_argument("jti", help="The JTI of the coupon")
    revoke_parser.add_argument("--reason", default="unspecified", help="Reason for revocation")

    # Public key
    subparsers.add_parser("public-key", help="Fetch and print CA public key")

    args = parser.parse_args()

    _configure_logging(args.debug)

    # Cache backend selection
    if args.cache == "none":
        storage = NullStorage()
        cache_enabled = False
    elif args.cache == "memory":
        storage = InMemoryStorage()
        cache_enabled = True
    else:
        storage = FileStorage(args.cache_path)
        cache_enabled = True

    public_key_pem: str | None = None
    if args.public_key:
        p = Path(args.public_key).expanduser()
        if p.exists() and p.is_file():
            public_key_pem = p.read_text(encoding="utf-8")
        else:
            public_key_pem = args.public_key

    client = DiscClient(
        base_url=args.url,
        timeout_seconds=args.timeout,
        max_retries=args.retries,
        backoff_factor=args.backoff,
        cache=cache_enabled,
        storage=storage,
        offline=args.offline,
        offline_strategy=args.offline_strategy,
        public_key_pem=public_key_pem,
        auto_fetch_public_key=True if args.offline and args.offline_strategy in {"local", "auto"} else False,
    )

    try:
        if args.command == "mint":
            result = client.issue_coupon(args.audience, args.scope, args.ttl)
            if args.raw and isinstance(result, dict) and isinstance(result.get("coupon"), str):
                print(result["coupon"])
            else:
                print(json.dumps(result, indent=2))
        elif args.command in ("verify", "validate"):
            token = args.token
            if token == "-":
                token = sys.stdin.read().strip()
            result = client.verify_coupon(token)
            if args.raw:
                print("true" if result.get("valid") else "false")
            else:
                print(json.dumps(result, indent=2))
            # Conventional exit code: 0=valid, 2=invalid
            if result.get("valid") is False:
                raise SystemExit(2)
        elif args.command == "revoke":
            result = client.revoke_coupon(args.jti, args.reason)
            print(json.dumps(result, indent=2))
        elif args.command == "public-key":
            pem = client.get_public_key_pem()
            print(pem)
        else:
            parser.print_help()
            raise SystemExit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1)

    raise SystemExit(0)

if __name__ == "__main__":
    main()
