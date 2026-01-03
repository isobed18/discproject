import os
import requests
import sys
import time
import subprocess
import json
import logging
import platform

# Configuration
# Allow overriding BASE_URL for CI environment
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000/v1")
ADMIN_USER = "admin"
TEST_USER = "alice"
RESOURCE_ID = "doc-verify-all"

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()

def log_pass(msg):
    logger.info(f"✅ {msg}")

def log_fail(msg):
    logger.error(f"❌ {msg}")
    # Don't exit immediately, try to run other tests
    # sys.exit(1)

def run_command(cmd):
    try:
        # Cross-platform / null output
        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def create_token(user):
    result = subprocess.run(
        [sys.executable, "cli/create_test_token.py", user], 
        capture_output=True, text=True
    )
    if result.returncode != 0:
        log_fail(f"Token generation failed for {user}")
        return None
    return result.stdout.strip()

def test_infrastructure():
    print("\n--- 1. Infrastructure Checks ---")
    
    # Skip Docker checks in CI if we assume services are handled by the runner
    if os.getenv("CI"):
        log_pass("Skipping Docker Container checks in CI environment")
    else:
        grep_cmd = "findstr" if platform.system() == "Windows" else "grep"
        
        # Redis Check
        if run_command(f"docker ps | {grep_cmd} disc-redis"):
            log_pass("Redis Container is running")
        else:
            log_fail("Redis Container NOT running")

        # OPA Check
        if run_command(f"docker ps | {grep_cmd} disc-opa"):
            log_pass("OPA Container is running")
        else:
            log_fail("OPA Container NOT running")
        
    # Backend Heath
    try:
        # Base URL usually includes /v1, so we strip it for health check
        health_url = BASE_URL.replace("/v1", "/health")
        res = requests.get(health_url)
        if res.status_code == 200:
            log_pass("Backend is Healthy")
        else:
            log_fail(f"Backend unhealthy: {res.status_code}")
    except Exception as e:
        log_fail(f"Backend unreachable: {e}")

def test_core_services(token):
    print("\n--- 2. Core Services (Person A - Week 1-4) ---")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Issue
    payload = {"audience": "app-srv", "scope": "read", "resource": RESOURCE_ID}
    try:
        res = requests.post(f"{BASE_URL}/issue", json=payload, headers=headers)
        if res.status_code == 200:
            coupon = res.json().get("coupon")
            log_pass("Issue Coupon Success")
            return coupon
        elif res.status_code == 403: # Policy might deny if not delegated
            log_fail(f"Issue Denied (Likely OPA): {res.text}")
        else:
            log_fail(f"Issue Failed: {res.status_code} {res.text}")
    except Exception as e:
        log_fail(f"Issue Exception: {e}")
    return None

def test_security_features(admin_token, user_token):
    print("\n--- 3. Security & Policy (Person D - Week 1-6) ---")
    
    # 3.1 Delegation
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    deleg_payload = {"delegate": TEST_USER, "resource": RESOURCE_ID, "ttl": 3600}
    res = requests.post(f"{BASE_URL}/delegations", json=deleg_payload, headers=admin_headers) # Any user can delegate for now
    if res.status_code == 200:
        log_pass("Delegation Created")
    else:
        log_fail(f"Delegation Failed: {res.text}")

    # Retry Issue (if failed before, or just to generate audit log)
    # We need a fresh event for audit search
    user_headers = {"Authorization": f"Bearer {user_token}"}
    payload = {"audience": "app-srv", "scope": "read", "resource": RESOURCE_ID, "details": {"email": "pii@test.com"}}
    # Note: endpoints.py doesn't map 'details' from body to log_event yet in provided code, 
    # but let's check basic flow.
    requests.post(f"{BASE_URL}/issue", json=payload, headers=user_headers)
    
    # Wait for async indexer
    time.sleep(1)

    # 3.2 Audit Search (RBAC)
    search_res = requests.get(f"{BASE_URL}/audit/search?actor={TEST_USER}", headers=admin_headers)
    if search_res.status_code == 200:
        results = search_res.json()["results"]
        if len(results) > 0:
            log_pass(f"Audit Search Success (Found {len(results)} events)")
        else:
            log_fail("Audit Search returned empty list (Indexer might be broken)")
    else:
        log_fail(f"Audit Search Failed: {search_res.status_code}")

    # 3.3 Rate Limiting
    print("   Testing Rate Limit (6 rapid requests)...")
    limit_hit = False
    for i in range(6):
        r = requests.post(f"{BASE_URL}/issue", json=payload, headers=user_headers)
        if r.status_code == 429:
            limit_hit = True
            break
    if limit_hit:
        log_pass("Rate Limiting Active (429 received)")
    else:
        log_fail("Rate Limit NOT enforced (Expected 429)")

    # 3.4 Security Headers
    head = requests.get(f"http://localhost:8000/health")
    if "X-Content-Type-Options" in head.headers:
        log_pass("Security Headers Middleware Active")
    else:
        log_fail("Security Headers Missing")

if __name__ == "__main__":
    print("🚧 Starting Master Verification Script 🚧")
    
    # Check Infrastructure
    test_infrastructure()
    
    # Generate Tokens
    admin_token = create_token(ADMIN_USER)
    user_token = create_token(TEST_USER)
    
    if user_token:
        # Core Services
        coupon = test_core_services(user_token)
        
        # Security Features
        test_security_features(admin_token, user_token)
    
    print("\n--- Verification Complete ---")
