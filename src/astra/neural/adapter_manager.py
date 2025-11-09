"""
AdapterManager
- Registry for adapters (LoRA/PEFT). Stores metadata, signatures, mount status.
- Lightweight JSON-backed store for prototypes; replace with SQL/KeyValue in production.
- Provides add_adapter(), list_adapters(), get_adapter(), sign_adapter(), verify_signature(), load_adapter().
"""

from __future__ import annotations
import os
import json
import hashlib
import hmac
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("astra.adapter_manager")
logger.setLevel(logging.INFO)

ADAPTER_STORE = os.environ.get("ASTRA_ADAPTER_STORE", "./adapters.json")
SIGNING_KEY = os.environ.get("ASTRA_ADAPTER_SIGNING_KEY", "change_me_in_prod")  # store securely in production

def _load_store() -> Dict[str, Any]:
    if os.path.exists(ADAPTER_STORE):
        with open(ADAPTER_STORE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_store(data: Dict[str, Any]) -> None:
    with open(ADAPTER_STORE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

class AdapterManager:
    def __init__(self):
        self.store = _load_store()

    def list_adapters(self) -> list[Dict[str, Any]]:
        return self.store.get("adapters", [])

    def get_adapter(self, adapter_id: str) -> Optional[Dict[str, Any]]:
        for a in self.list_adapters():
            if a.get("id") == adapter_id:
                return a
        return None

    def add_adapter(self, adapter_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        adapters = self.store.setdefault("adapters", [])
        if self.get_adapter(adapter_id):
            raise RuntimeError("adapter exists")
        meta = {"id": adapter_id, "created_at": datetime.utcnow().isoformat()+"Z", "metadata": metadata, "signature": None}
        adapters.append(meta)
        _save_store(self.store)
        return meta

    def sign_adapter(self, adapter_id: str) -> Dict[str, Any]:
        a = self.get_adapter(adapter_id)
        if not a:
            raise RuntimeError("adapter not found")
        payload = json.dumps(a["metadata"], sort_keys=True, separators=(",", ":")).encode()
        signature = hmac.new(SIGNING_KEY.encode(), payload, digestmod=hashlib.sha256).hexdigest()
        a["signature"] = signature
        _save_store(self.store)
        return {"id": adapter_id, "signature": signature}

    def verify(self, adapter_id: str, signature: str) -> bool:
        a = self.get_adapter(adapter_id)
        if not a:
            return False
        payload = json.dumps(a["metadata"], sort_keys=True, separators=(",", ":")).encode()
        expected = hmac.new(SIGNING_KEY.encode(), payload, digestmod=hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def load_adapter(self, adapter_id: str, model_bridge) -> Dict[str, Any]:
        """
        Instruct model_bridge to mount adapter (if supported).
        Returns model_bridge response plus adapter metadata.
        """
        a = self.get_adapter(adapter_id)
        if not a:
            raise RuntimeError("adapter not found")
        # ensure signed
        if not a.get("signature"):
            raise RuntimeError("adapter not signed")
        # call model bridge to load adapter (model-specific)
        resp = await model_bridge.load_adapter(adapter_id)
        return {"adapter": a, "load_result": resp}