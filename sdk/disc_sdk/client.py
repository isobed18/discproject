import httpx
from typing import Optional, Dict, Any

class DiscClient:
    def __init__(self, base_url: str = "http://localhost:8000/v1"):
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url)

    def issue_coupon(self, audience: str, scope: str, ttl_seconds: int = 300) -> Dict[str, Any]:
        """
        Issue a new coupon.
        """
        response = self.client.post("/issue", json={
            "audience": audience,
            "scope": scope,
            "ttl_seconds": ttl_seconds
        })
        response.raise_for_status()
        return response.json()

    def verify_coupon(self, coupon: str) -> Dict[str, Any]:
        """
        Verify a coupon.
        """
        response = self.client.post("/verify", json={"coupon": coupon})
        if response.status_code != 200:
            print(f"Verify failed: {response.status_code} {response.text}")
        response.raise_for_status()
        return response.json()

    def revoke_coupon(self, jti: str, reason: str = "unspecified") -> Dict[str, Any]:
        """
        Revoke a coupon.
        """
        response = self.client.post("/revoke", json={"jti": jti, "reason": reason})
        response.raise_for_status()
        return response.json()
