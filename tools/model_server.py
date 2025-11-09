"""
Model Server Reference for ASTRA

Provides:
 - GET  /health
 - POST /generate  {"prompt","max_tokens","temperature","top_p","adapter_ids","meta"}
 - POST /adapter/load {"adapter_id"}  (in-memory mount stub)

Modes:
 - CLI mode: wraps an external binary (set ASTRA_MODEL_SERVER_MODE=cli and provide LLAMA_CLI_CMD env)
 - TRANSFORMERS mode: uses HuggingFace transformers if available (set ASTRA_MODEL_SERVER_MODE=transformers)

Usage examples:
  # CLI mode (llama.cpp)
  export ASTRA_MODEL_SERVER_MODE="cli"
  export LLAMA_CLI_CMD="./main -m /models/model.gguf -p {prompt} -n {max_tokens}"
  uvicorn tools.model_server:app --reload --port 8001

  # Transformers (dev only)
  export ASTRA_MODEL_SERVER_MODE="transformers"
  export TRANSFORMER_MODEL_NAME="gpt2"
  uvicorn tools.model_server:app --reload --port 8001
"""

from __future__ import annotations
import os
import shlex
import subprocess
import asyncio
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
import html
import uuid

logger = logging.getLogger("astra.model_server")
logger.setLevel(logging.INFO)

# Config via env
MODE = os.environ.get("ASTRA_MODEL_SERVER_MODE", "cli").lower()  # "cli" or "transformers"
LLAMA_CLI_CMD = os.environ.get("LLAMA_CLI_CMD", None)  # e.g. "./main -m /models/model.gguf -p {prompt} -n {max_tokens}"
TRANSFORMER_MODEL_NAME = os.environ.get("TRANSFORMER_MODEL_NAME", "gpt2")
TRANSFORMER_DEVICE = os.environ.get("TRANSFORMER_DEVICE", "cpu")  # "cpu" or "cuda"

# optional transformers imports (lazy)
_transformers = None
_text_generation_pipeline = None

def lazy_load_transformers():
    global _transformers, _text_generation_pipeline
    if _transformers is not None and _text_generation_pipeline is not None:
        return
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
        _transformers = (AutoModelForCausalLM, AutoTokenizer, pipeline)
        # create pipeline
        tokenizer = AutoTokenizer.from_pretrained(TRANSFORMER_MODEL_NAME)
        model = AutoModelForCausalLM.from_pretrained(TRANSFORMER_MODEL_NAME)
        device = 0 if TRANSFORMER_DEVICE == "cuda" else -1
        _text_generation_pipeline = pipeline("text-generation", model=model, tokenizer=tokenizer, device=device)
        logger.info("Transformers pipeline loaded: %s device=%s", TRANSFORMER_MODEL_NAME, TRANSFORMER_DEVICE)
    except Exception as e:
        logger.exception("Failed to load transformers: %s", e)
        raise

# simple in-memory adapter registry (for demonstration)
ADAPTER_REGISTRY: Dict[str, Dict[str, Any]] = {}

app = FastAPI(title="ASTRA Model Server (Reference)", version="0.1")

class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = 256
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.95
    adapter_ids: Optional[List[str]] = []
    meta: Optional[Dict[str,Any]] = {}

class AdapterLoadRequest(BaseModel):
    adapter_id: str

def _now_iso():
    return datetime.utcnow().isoformat() + "Z"

@app.get("/health")
async def health():
    return {"ok": True, "mode": MODE, "time": _now_iso()}

@app.post("/generate")
async def generate(req: GenerateRequest):
    # Basic validation
    if not req.prompt or len(req.prompt.strip()) == 0:
        raise HTTPException(status_code=400, detail="prompt is required")

    # Small resource guard
    if len(req.prompt) > 200_000:
        raise HTTPException(status_code=413, detail="prompt too large")

    request_id = str(uuid.uuid4())
    provenance = {"request_id": request_id, "received_at": _now_iso(), "adapter_ids": req.adapter_ids or [], "meta": req.meta or {}}

    # Choose mode
    if MODE == "cli":
        if not LLAMA_CLI_CMD:
            raise HTTPException(status_code=500, detail="LLAMA_CLI_CMD not configured for CLI mode")

        # Safely inject prompt into command template
        # Note: the command template should use {prompt} and {max_tokens}
        try:
            safe_prompt = shlex.quote(req.prompt)
            cmd = LLAMA_CLI_CMD.format(prompt=req.prompt if "{prompt}" in LLAMA_CLI_CMD else safe_prompt, max_tokens=int(req.max_tokens))
        except Exception as e:
            logger.exception("Bad CLI command template: %s", e)
            raise HTTPException(status_code=500, detail=f"CLI template error: {e}")

        # Run in thread to avoid blocking event loop
        try:
            logger.info("CLI generate request %s: cmd=%s", request_id, cmd if len(cmd) < 200 else cmd[:200]+"...")
            proc = await asyncio.to_thread(subprocess.run, cmd, shell=True, capture_output=True, text=True, timeout=max(30, int(req.max_tokens/2 + 10)))
            out = proc.stdout.strip() or proc.stderr.strip()
            result = {"text": out, "returncode": proc.returncode}
            provenance["via"] = "cli"
            provenance["cmd"] = cmd
            provenance["latency_seconds"] = None  # could be measured around subprocess call
            return JSONResponse({"request_id": request_id, "result": result, "provenance": provenance})
        except subprocess.TimeoutExpired as e:
            logger.warning("CLI timeout: %s", e)
            raise HTTPException(status_code=504, detail="model CLI timeout")
        except Exception as e:
            logger.exception("CLI generate error: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    elif MODE == "transformers":
        # run pipeline (lazy load)
        try:
            lazy_load_transformers()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"transformers backend failed to load: {e}")

        try:
            # call generation
            # control tokens: num_return_sequences = 1
            params = {"max_length": int(req.max_tokens) + 32, "temperature": float(req.temperature), "top_p": float(req.top_p), "do_sample": True}
            logger.info("Transformers generate request %s: prompt len=%d", request_id, len(req.prompt))
            out = await asyncio.to_thread(_text_generation_pipeline, req.prompt, **params)
            # pipeline returns list of dicts with 'generated_text'
            text = out[0].get("generated_text") if isinstance(out, list) and len(out) > 0 else str(out)
            provenance["via"] = "transformers"
            provenance["latency_seconds"] = None
            return JSONResponse({"request_id": request_id, "result": {"text": text}, "provenance": provenance})
        except Exception as e:
            logger.exception("Transformers generate error: %s", e)
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=500, detail=f"unsupported server mode: {MODE}")

@app.post("/adapter/load")
async def adapter_load(req: AdapterLoadRequest):
    # This is a light-weight demo: we "mount" the adapter into the registry if signed metadata exists.
    adapter_id = req.adapter_id
    # For the reference server we simply mark it loaded
    ADAPTER_REGISTRY[adapter_id] = {"loaded_at": _now_iso(), "adapter_id": adapter_id, "status": "loaded"}
    logger.info("Adapter loaded: %s", adapter_id)
    return {"ok": True, "adapter_id": adapter_id, "status": "loaded", "time": _now_iso()}

@app.get("/adapter/status")
async def adapter_status(adapter_id: Optional[str] = None):
    if adapter_id:
        return ADAPTER_REGISTRY.get(adapter_id, {"ok": False, "reason":"not found"})
    return {"adapters": list(ADAPTER_REGISTRY.keys())}

# small root for sanity
@app.get("/")
async def root():
    return {"service": "astra-model-server", "mode": MODE, "time": _now_iso()}