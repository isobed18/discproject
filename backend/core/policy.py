import requests
import json
import logging
from typing import Dict, Any
from .config import settings

logger = logging.getLogger(__name__)


class PolicyEngine:
    def __init__(self, opa_url: str = settings.OPA_URL):
        # OPA base URL (ör: http://host.docker.internal:8182)
        self.opa_url = opa_url.rstrip("/")

        # Evaluation endpoint
        self.eval_url = f"{self.opa_url}/v1/data/disc/authz/allow"

    def check_permission(self, input_data: Dict[str, Any]) -> bool:
        """
        Queries OPA for a policy decision.
        """
        try:
            payload = {"input": input_data}

            logger.info("OPA INPUT:\n%s", json.dumps(payload, indent=2))

            response = requests.post(
                self.eval_url,
                json=payload,
                timeout=2.0
            )

            logger.info("OPA STATUS: %s", response.status_code)
            logger.info("OPA RESPONSE: %s", response.text)

            response.raise_for_status()

            data = response.json()

            # Expected shape: { "result": true }
            if isinstance(data.get("result"), bool):
                return data["result"]

            # Alternative shape: { "result": { "allow": true } }
            return data.get("result", {}).get("allow", False)

        except requests.exceptions.RequestException as e:
            logger.error("OPA request failed: %s", e)

            if settings.DEV_MODE:
                logger.warning("DEV_MODE enabled, allowing request")
                return True

            return False


# Singleton
policy_engine = PolicyEngine()
