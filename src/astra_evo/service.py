# service.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
from .validate import run_validation, gates_decision
from .gguf_io import apply_rope_tuning, GGUFIO
from .provenance import sign_file, verify_signature
import shutil, os, json, time

app = FastAPI(title="ASTRA Evolution Service")

class PatchOps(BaseModel):
    quantize: Optional[str] = None
    loraPaths: list[str] = []
    ropeBase: Optional[float] = 1e6
    ropeScale: Optional[float] = 1.0
    repack: bool = True

class PatchReq(BaseModel):
    basePath: str
    ops: PatchOps
    preview: bool = True

class ValidateReq(BaseModel):
    basePath: str
    outPath: str
    evalDir: str

class SignReq(BaseModel):
    outPath: str
    meta: dict = {}

class CommitReq(BaseModel):
    outPath: str
    requireCanary: bool = False

@app.get("/gguf/inspect")
def inspect(path: str):
    io = GGUFIO(path)
    header = {
        "arch": io.kv_get("general.arch", "GPT-OOS-20B"),
        "quant": io.kv_get("quantization", "Q4_K_M"),
        "ctxLen": io.kv_get("ctx_len", 8192),
        "vocabSize": io.kv_get("vocab_size", 128000),
        "tensors": io.kv_get("tensors", 291),
    }
    return {"header": header, "meta": {k: v for k, v in io.kv.items()}}

@app.post("/gguf/patch")
def patch(req: PatchReq):
    # snapshot
    stamp = time.strftime("%Y%m%d_%H%M%S")
    snap_dir = Path("snapshots") / stamp
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap_path = snap_dir / "model.gguf"
    shutil.copy2(req.basePath, snap_path)

    # (placeholder) produce outPath; real implementation merges LoRAs + quant/repack
    out_path = Path(req.basePath).with_suffix(".EVO.gguf")
    shutil.copy2(req.basePath, out_path)

    # apply RoPE KV mutations if requested
    if req.ops.ropeBase is not None or req.ops.ropeScale is not None:
        apply_rope_tuning(str(out_path), req.ops.ropeBase or 1e6, req.ops.ropeScale or 1.0)

    # preview stats (dummy deltas; wire real stats from lora_merge/preview)
    preview = {
        "changedTensors": 84 if req.ops.loraPaths or req.ops.quantize else 12,
        "bytesDeltaMB": -2200 if req.ops.quantize else -150,
        "heatmapVec": [0.0] * (64 * 24),
    }
    (snap_dir / "manifest.json").write_text(json.dumps({"basePath": req.basePath, "ops": req.ops.dict()}, indent=2))
    return {"preview": preview, "outPath": str(out_path), "snapshotId": str(snap_dir)}

@app.post("/gguf/validate") 
def validate(req: ValidateReq):
    res = run_validation(req.basePath, req.outPath, req.evalDir)
    # baseline ppl is estimated from base model by reusing ppl scorer
    from .validate import score_ppl
    base_ppl = score_ppl(Path(req.basePath), Path(req.evalDir) / "text_tiny.txt")
    decision = gates_decision(base_ppl, res)
    return {
        "ppl": res.ppl, "toolAcc": res.toolAcc, "drift": res.drift, "guardrail": res.guardrail,
        "logs": res.logs, "pplDelta": decision["pplDelta"],
        "block": decision["block"], "forceCanary": decision["forceCanary"],
        "thresholds": decision["thresholds"]
    }

@app.post("/gguf/sign")
def sign(req: SignReq):
    return sign_file(req.outPath, req.meta)

@app.post("/gguf/commit")
def commit(req: CommitReq):
    # verify signature before commit
    if not verify_signature(req.outPath):
        raise HTTPException(400, "Signature verification failed; refuse commit.")
    # canary path: write .EVO.gguf but do not overwrite base
    final_path = req.outPath
    if req.requireCanary:
        return {"status": "canary", "finalPath": final_path}
    # (if you want to replace base atomically, do it here)
    return {"status": "committed", "finalPath": final_path}
        
        return PatchResponse(
            status="success",
            message="Model patching complete",
            preview=preview,
            out_path=str(out_path),
            snapshot_id=snapshot_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/gguf/validate")
async def validate_model(
    base_path: str,
    evolved_path: str,
    eval_dir: str
) -> ValidateResponse:
    """Validate evolved model against gates."""
    try:
        validator = ModelValidator(
            Path(base_path),
            Path(evolved_path),
            Path(eval_dir)
        )
        
        results = validator.run_all_checks()
        
        return ValidateResponse(
            status="success",
            message="Validation complete",
            **results
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/gguf/sign")
async def sign_model(model_path: str) -> SignResponse:
    """Sign evolved model."""
    try:
        signer = ModelSigner()
        checksum, signature = signer.sign_model(Path(model_path))
        
        return SignResponse(
            status="success",
            message="Model signed successfully",
            checksum=checksum,
            signature=signature
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/gguf/commit")
async def commit_model(model_path: str) -> GGUFResponse:
    """Commit evolved model."""
    try:
        signer = ModelSigner()
        final_path = signer.commit_model(Path(model_path))
        
        return GGUFResponse(
            status="success",
            message=f"Model committed to {final_path}"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/gguf/rollback")
async def rollback_model(model_path: str) -> GGUFResponse:
    """Rollback model to previous state."""
    try:
        signer = ModelSigner()
        signer.rollback_model(Path(model_path))
        
        return GGUFResponse(
            status="success",
            message="Model rolled back successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))