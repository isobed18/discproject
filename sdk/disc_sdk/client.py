import httpx
import time
import logging
from typing import Optional, Dict, Any, Mapping, Callable

logger = logging.getLogger("disc_sdk")

class DiscClient:
    """Lightweight DISC SDK client.

    Week 3 requirement: support passing through tracing headers (e.g. `traceparent`).
    Week 2 requirement (Remediation): Retry logic with backoff.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        *,
        tracing_headers: Optional[Mapping[str, str]] = None,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        self.base_url = base_url
        self._tracing_headers: Dict[str, str] = dict(tracing_headers or {})
        self.client = httpx.Client(base_url=base_url, timeout=timeout_seconds)
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Internal wrapper to handle retries for transient errors."""
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.request(method, url, **kwargs)
                # Retry on server errors (500, 502, 503, 504)
                if response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"Server error {response.status_code}", request=response.request, response=response
                    )
                return response
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.HTTPStatusError) as e:
                last_exception = e
                if attempt < self.max_retries:
                    sleep_time = self.backoff_factor * (2 ** attempt)
                    logger.warning(f"Request failed ({e}), retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    logger.error("Max retries exceeded.")
        
        if last_exception:
            raise last_exception
        raise httpx.RequestError("Unknown retry error")

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
        Issue a new coupon (with retries).
        """
        response = self._request_with_retry(
            "POST",
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
