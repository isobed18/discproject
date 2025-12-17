import requests
import json
import logging
from typing import Dict, Any

# DÜZELTME: Absolute Import (Noktayı sildik)
from core.config import settings

logger = logging.getLogger(__name__)

class PolicyEngine:
    def __init__(self, opa_url: str = settings.OPA_URL):
        self.opa_url = opa_url.rstrip("/")
        # OPA'nın standart REST API endpoint'i
        self.eval_url = f"{self.opa_url}/v1/data/disc/authz/allow"

    def check_permission(self, input_data: Dict[str, Any]) -> bool:
        try:
            payload = {"input": input_data}
            
            # --- DEBUG LOG ---
            # OPA'ya tam olarak ne gönderdiğimizi görmek için bunu ekliyoruz.
            # Loglarda "DEBUG: OPA INPUT:" diye aratacağız.
            print(f"DEBUG: OPA INPUT: {json.dumps(payload, indent=2)}") 
            # -----------------

            response = requests.post(
                self.eval_url,
                json=payload,
                timeout=2.0
            )
            response.raise_for_status()
            data = response.json()

            # OPA bazen direkt boolean, bazen JSON döner. İkisini de kapsayalım:
            if isinstance(data.get("result"), bool):
                return data["result"]

            return data.get("result", {}).get("allow", False)

        except Exception as e:
            logger.error("OPA request failed: %s", e)
            # Dev modundaysak ve OPA kapalıysa geçici izin ver (Opsiyonel)
            if settings.DEV_MODE:
                return True
            return False

policy_engine = PolicyEngine()