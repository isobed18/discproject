import httpx
from typing import Dict, Any
from .config import settings

class PolicyEngine:
    def __init__(self, opa_url: str = settings.OPA_URL):
        self.opa_url = opa_url

    def check_permission(self, input_data: Dict[str, Any]) -> bool:
        """
        Queries OPA to make an authorization decision.
        
        Args:
            input_data: The context (user, action, resource, delegations)
            
        Returns:
            bool: True if allowed, False otherwise.
        """
        try:
            # We use httpx for synchronous request here (or use async in async endpoints)
            # Using synchronous for simplicity in this MVP context
            import requests
            response = requests.post(
                self.opa_url,
                json={"input": input_data},
                timeout=2.0 # Fail fast
            )
            
            if response.status_code == 200:
                result = response.json()
                # OPA returns {"result": true} for a boolean query
                return result.get("result", False)
            else:
                print(f"OPA Error: {response.text}")
                return False

        except Exception as e:
            # Fail-Open or Fail-Closed based on Config
            if settings.DEV_MODE:
                print(f"WARNING: OPA Unreachable ({e}). Allowing request due to DEV_MODE.")
                return True
            
            print(f"Policy Engine Error: {e}")
            return False

policy_engine = PolicyEngine()