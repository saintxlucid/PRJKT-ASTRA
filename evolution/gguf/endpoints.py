"""FastAPI endpoints for GGUF Metamorphosis Chamber."""

import os
from typing import Dict, List, Optional, Any
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .patcher import (
    GGUFPatcher,
    GGUFModelInspector,
    GGUFPatcherError,
    PatchOps,
    PatchPreview,
    ValidationResult
)

# Initialize FastAPI app
app = FastAPI(
    title="ASTRA GGUF Metamorphosis Chamber",
    description="Model evolution endpoints for GGUF artifacts",
    version="2.0.0"
)

# Initialize components
SNAPSHOT_DIR = Path("Snapshots")
SNAPSHOT_DIR.mkdir(exist_ok=True)

SECRET = os.environ.get("ASTRA_OPERATOR_SECRET", "dev-only-change-me")

inspector = GGUFModelInspector()
patcher = GGUFPatcher(snapshot_dir=SNAPSHOT_DIR)

# Request/Response Models
class InspectResponse(BaseModel):
    """Response model for model inspection."""
    header: Dict[str, Any]
    meta: Dict[str, Any]

class PatchRequest(BaseModel):
    """Request model for patch operations."""
    base_path: str
    ops: PatchOps
    preview: bool = True
    base_f16_path: Optional[str] = None

class PatchResponse(BaseModel):
    """Response model for patch operations."""
    preview: Dict[str, Any]
    out_path: str
    snapshot_id: str

class ValidateRequest(BaseModel):
    """Request model for model validation."""
    out_path: str
    dataset: str

class ValidateResponse(BaseModel):
    """Response model for validation results."""
    ppl: float
    acc: float
    drift: float
    logs: List[str]

class SignRequest(BaseModel):
    """Request model for model signing."""
    out_path: str
    meta: Dict[str, Any]

class SignResponse(BaseModel):
    """Response model for signing results."""
    checksum: str
    signature: str

class CommitRequest(BaseModel):
    """Request model for model commit."""
    out_path: str
    signature: str
    canary: bool = True

class CommitResponse(BaseModel):
    """Response model for commit results."""
    status: str = "committed"
    final_path: str

class RollbackRequest(BaseModel):
    """Request model for rollback operation."""
    snapshot_id: str

# Error handler
@app.exception_handler(GGUFPatcherError)
async def patcher_error_handler(request, exc: GGUFPatcherError):
    """Handle patcher-specific errors."""
    return {
        "error": str(exc),
        "type": "GGUFPatcherError"
    }

# Endpoints
@app.get("/gguf/inspect", response_model=InspectResponse)
async def inspect_model(path: str):
    """Inspect GGUF model header and metadata."""
    try:
        header, meta = inspector.inspect(path)
        return {
            "header": {
                "vocab_size": header.vocab_size,
                "ctx_len": header.ctx_len,
                "arch": header.arch,
                "quant": header.quant,
                "rope_base": header.rope_base,
                "rope_scale": header.rope_scale,
                "tensors": header.tensors
            },
            "meta": meta
        }
    except GGUFPatcherError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gguf/patch", response_model=PatchResponse)
async def patch_model(req: PatchRequest):
    """Preview or apply patch operations."""
    try:
        # First get preview
        preview = patcher.preview_patch(req.base_path, req.ops)
        
        # Apply patch if not preview mode
        if not req.preview:
            out_path = patcher.apply_patch(
                preview,
                req.ops,
                req.base_f16_path
            )
            preview.out_path = out_path
            
        return {
            "preview": {
                "changed_tensors": preview.preview.changed_tensors,
                "bytes_delta_mb": preview.preview.bytes_delta_mb,
                "heatmap_vec": preview.preview.heatmap_vec
            },
            "out_path": preview.out_path,
            "snapshot_id": preview.snapshot_id
        }
    except GGUFPatcherError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gguf/validate", response_model=ValidateResponse)
async def validate_model(req: ValidateRequest):
    """Validate evolved model."""
    try:
        result = patcher.validate(req.out_path, req.dataset)
        return {
            "ppl": result.ppl,
            "acc": result.acc,
            "drift": result.drift,
            "logs": result.logs
        }
    except GGUFPatcherError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gguf/sign", response_model=SignResponse)
async def sign_model(req: SignRequest):
    """Sign evolved model."""
    try:
        checksum, signature = patcher.sign(
            req.out_path,
            req.meta,
            SECRET
        )
        return {
            "checksum": f"sha256:{checksum}",
            "signature": signature
        }
    except GGUFPatcherError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gguf/commit", response_model=CommitResponse)
async def commit_model(req: CommitRequest):
    """Commit evolved model."""
    try:
        final_path = patcher.commit(
            req.out_path,
            req.signature,
            SECRET,
            req.canary
        )
        return {
            "status": "committed",
            "final_path": final_path
        }
    except GGUFPatcherError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gguf/rollback")
async def rollback_model(req: RollbackRequest):
    """Rollback to snapshot."""
    try:
        patcher.rollback(req.snapshot_id)
        return {"status": "rolled back"}
    except GGUFPatcherError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))