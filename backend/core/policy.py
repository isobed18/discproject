import requests
from typing import Dict, Any, Optional
from .config import settings
import logging

logger = logging.getLogger(__name__)

class PolicyEngine:
    def __init__(self, opa_url: str = settings.OPA_URL):
        self.opa_url = opa_url

    def check_permission(self, input_data: Dict[str, Any]) -> bool:
        """
        Queries OPA for a policy decision.
        
        Args:
            input_data: The input dictionary to send to OPA. 
                        Structure typically: {"input": {...}}
        
        Returns:
            bool: True if allowed, False otherwise.
        """
        try:
            # Policy path in OPA is /v1/data/disc/authz
            # We expect the rule 'allow' to be returned.
            response = requests.post(
                self.opa_url,
                json={"input": input_data},
                timeout=1.0 # Fail fast
            )
            response.raise_for_status()
            
            result = response.json()
            # OPA returns {"result": {"allow": true}} or just {"result": true} depending on query
            # If we query the package base, we get all rules.
            # Let's assume we query the base 'authz' and look for 'allow'.
            
            decision = result.get("result", {}).get("allow", False)
            return decision

        except requests.exceptions.RequestException as e:
            # For MVP, we log and fail closed (deny access) unless in DEV_MODE
            if settings.DEV_MODE:
                logger.warning(f"OPA Unreachable in DEV_MODE. Allowing request. Error: {e}")
                return True
            logger.error(f"Policy Engine Error: {e}")
            return False

# Singleton instance
policy_engine = PolicyEngine()
