import subprocess
import json
import sys

def run_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed: {command}")
        print(result.stderr)
        sys.exit(1)
    return result.stdout.strip()

# 1. Mint
print("Minting coupon...")
mint_output = run_command("python cli/disc-cli.py --url http://localhost:8001/v1 mint --audience test-service --scope read:data")
print(mint_output)
mint_data = json.loads(mint_output)
coupon = mint_data["coupon"]

# 2. Verify
print(f"\nVerifying coupon: {coupon}")
verify_output = run_command(f'python cli/disc-cli.py --url http://localhost:8001/v1 verify "{coupon}"')
print(verify_output)
verify_data = json.loads(verify_output)

if verify_data.get("valid") is True:
    print("\nSUCCESS: Coupon verified.")
else:
    print("\nFAILURE: Coupon verification failed.")
    sys.exit(1)
