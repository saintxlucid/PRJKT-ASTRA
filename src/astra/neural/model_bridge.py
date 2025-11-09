"""
ModelBridge
- Primary async client to a local LLM inference endpoint (assumes HTTP API at http://127.0.0.1:8001).
- Falls back to running a local llama.cpp binary if HTTP endpoint isn't available (simple subprocess wrapper).
- Provides: health(), infer(prompt,...), load_adapter(adapter_id) (stub, model dependent).
"""

from __future__ import annotations
import os
import asyncio
import json
import logging
from typing import Optional, Dict, Any
import httpx
import subprocess
import shlex
from time import time

logger = logging.getLogger("astra.model_bridge")
logger.setLevel(logging.INFO)

DEFAULT_HTTP_ENDPOINT = os.environ.get("ASTRA_MODEL_HTTP", "http://127.0.0.1:8001")

class ModelBridge:
    def __init__(self, endpoint: str = DEFAULT_HTTP_ENDPOINT, cli_fallback_cmd: Optional[str] = None, timeout: float = 30.0):
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.cli_fallback_cmd = cli_fallback_cmd or os.environ.get("ASTRA_LLAMA_CPP_CMD")  # example: "./main -m /models/model.gguf -p '{prompt}' -n {max_tokens}"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def health(self) -> Dict[str, Any]:
        """
        Check HTTP endpoint; return dict {ok: bool, details: ...}
        """
        try:
            c = await self._get_client()
            resp = await c.get(f"{self.endpoint}/health")
            if resp.status_code == 200:
                return {"ok": True, "status": resp.json()}
            return {"ok": False, "status_code": resp.status_code, "text": resp.text}
        except Exception as e:
            # try CLI quick-check if available
            if self.cli_fallback_cmd:
                try:
                    # non-blocking small check
                    p = subprocess.run(shlex.split(self.cli_fallback_cmd + " --version"), capture_output=True, text=True, timeout=2)
                    return {"ok": True, "fallback_cli": p.stdout.strip()}
                except Exception as e2:
                    return {"ok": False, "error_http": str(e), "error_cli": str(e2)}
            return {"ok": False, "error": str(e)}

    async def infer(self, prompt: str, max_tokens: int = 256, temperature: float = 0.7, top_p: float = 0.95, adapter_ids: Optional[list[str]] = None, meta: Optional[dict] = None) -> Dict[str, Any]:
        """
        Try HTTP inference first. If it fails and cli fallback exists, run subprocess fallback.
        Returns a dict: {text, tokens, latency, metadata}
        meta is arbitrary provenance metadata you want recorded.
        """
        metadata = meta or {}
        start = time()
        payload = {
            "prompt": prompt,
            "max_tokens": int(max_tokens),
            "temperature": float(temperature),
            "top_p": float(top_p),
            "adapter_ids": adapter_ids or [],
            "meta": metadata
        }
        # HTTP path
        try:
            c = await self._get_client()
            resp = await c.post(f"{self.endpoint}/generate", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                latency = time() - start
                data["_astra_provenance"] = {"latency": latency, "via": "http", "payload_meta": metadata}
                return data
            else:
                logger.warning("ModelBridge HTTP non-200: %s %s", resp.status_code, resp.text)
        except Exception as e:
            logger.debug("ModelBridge HTTP error: %s", e)

        # CLI fallback path
        if self.cli_fallback_cmd:
            try:
                # Build safe command (the CLI must accept prompt and tokens placeholders)
                cmd = self.cli_fallback_cmd.format(prompt=shlex.quote(prompt), max_tokens=max_tokens)
                logger.info("ModelBridge CLI fallback: %s", cmd)
                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=int(self.timeout))
                text = proc.stdout.strip() if proc.stdout else proc.stderr.strip()
                latency = time() - start
                return {"text": text, "tokens": None, "_astra_provenance": {"latency": latency, "via": "cli", "cmd": cmd, "returncode": proc.returncode, "meta": metadata}}
            except Exception as e:
                logger.exception("CLI fallback failed: %s", e)
                return {"error": str(e)}
        return {"error": "no inference path available (http failed, no cli fallback)", "meta": metadata}
    
    async def load_adapter(self, adapter_id: str) -> Dict[str, Any]:
        """
        Adapter loading is model-specific. This method asks endpoint to mount an adapter.
        If HTTP endpoint supports adapter control, this will call /adapter/load. Otherwise stub.
        """
        try:
            c = await self._get_client()
            resp = await c.post(f"{self.endpoint}/adapter/load", json={"adapter_id": adapter_id})
            if resp.status_code == 200:
                return resp.json()
            return {"ok": False, "status_code": resp.status_code, "text": resp.text}
        except Exception as e:
            logger.debug("Adapter load HTTP error (or not supported): %s", e)
            # fallback: no-op
            return {"ok": False, "error": "adapter control not supported by endpoint", "exception": str(e)}
            
    async def aclose(self):
        """Close HTTP client (idempotent)"""
        try:
            if self._client is not None:
                await self._client.aclose()
                self._client = None
        except Exception:
            pass