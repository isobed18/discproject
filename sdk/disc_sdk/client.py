import httpx
from typing import Optional, Dict, Any, Mapping

class DiscClient:
    """Lightweight DISC SDK client.

    Week 3 requirement: support passing through tracing headers (e.g. `traceparent`).
    This client accepts optional headers at construction time and/or per request.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        *,
        tracing_headers: Optional[Mapping[str, str]] = None,
        timeout_seconds: float = 10.0,
    ):
        self.base_url = base_url
        self._tracing_headers: Dict[str, str] = dict(tracing_headers or {})
        self.client = httpx.Client(base_url=base_url, timeout=timeout_seconds)

    def _merge_headers(self, headers: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
        merged: Dict[str, str] = {}
        merged.update(self._tracing_headers)
        if headers:
            merged.update(dict(headers))
        return merged

    def issue_coupon(
        self,
        audience: str,
        scope: str,
        ttl_seconds: int = 300,
        *,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Issue a new coupon.
        """
        response = self.client.post(
            "/issue",
            json={
            "audience": audience,
            "scope": scope,
            "ttl_seconds": ttl_seconds
            },
            headers=self._merge_headers(headers),
        )
        response.raise_for_status()
        return response.json()

    def verify_coupon(
        self,
        coupon: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Verify a coupon.
        """
        response = self.client.post(
            "/verify",
            json={"coupon": coupon},
            headers=self._merge_headers(headers),
        )
        if response.status_code != 200:
            print(f"Verify failed: {response.status_code} {response.text}")
        response.raise_for_status()
        return response.json()

    def revoke_coupon(
        self,
        jti: str,
        reason: str = "unspecified",
        *,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Revoke a coupon.
        """
        response = self.client.post(
            "/revoke",
            json={"jti": jti, "reason": reason},
            headers=self._merge_headers(headers),
        )
        response.raise_for_status()
        return response.json()
