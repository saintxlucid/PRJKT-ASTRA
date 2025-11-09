"""GGUF model surgery API endpoints."""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from pathlib import Path

from .surgeon import ModelSurgeon, ValidationMetrics, ModelPreviewResult

app = FastAPI(title="ASTRA Chamber")

# Initialize surgeon
surgeon = ModelSurgeon(
    cache_dir=".cache/metrics",
    validate_gates=True
)

class InspectResponse(BaseModel):
    """Response from model inspection."""
    header: Dict[str, Any]
    kv_store: Dict[str, Any]
    tensor_index: List[Dict[str, Any]]
    file_size: int
    tensor_count: int

class PatchRequest(BaseModel):
    """Request to patch a model."""
    base_path: str = Field(..., description="Path to base model")
    ops: Dict[str, Any] = Field(..., description="Operations to apply")
    preview: bool = Field(True, description="Whether to preview only")

class PatchResponse(BaseModel):
    """Response from patch operation."""
    changed_tensors: int
    bytes_delta_mb: float
    heatmap_vec: List[float]
    out_path: str
    snapshot_id: str

class ValidateRequest(BaseModel):
    """Request to validate a model."""
    model_path: str = Field(..., description="Path to model")
    dataset_path: str = Field(..., description="Path to eval dataset")
    cache_base: bool = Field(True, description="Cache base metrics")

class ValidateResponse(BaseModel):
    """Response from validation."""
    ppl: float
    acc: float
    drift: float
    guardrail: float
    logs: List[str]
    passed: bool

class SignRequest(BaseModel):
    """Request to sign a model."""
    model_path: str = Field(..., description="Path to model")
    ops: Dict[str, Any] = Field(..., description="Applied operations")

class SignResponse(BaseModel):
    """Response from signing."""
    checksum: str
    signature: str

class CommitRequest(BaseModel):
    """Request to commit model changes."""
    model_path: str = Field(..., description="Path to model")
    require_gates: bool = Field(True, description="Require passing gates")

@app.post("/gguf/inspect", response_model=InspectResponse)
async def inspect_model(model_path: str):
    """Inspect a GGUF model file."""
    try:
        result = surgeon.inspect(model_path)
        return InspectResponse(
            header=result.header,
            kv_store=result.kv_store,
            tensor_index=result.tensor_index,
            file_size=result.file_size,
            tensor_count=result.tensor_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gguf/patch", response_model=PatchResponse)
async def patch_model(req: PatchRequest):
    """Preview or apply model patches."""
    try:
        result = surgeon.preview(req.base_path, req.ops)
        return PatchResponse(
            changed_tensors=result.changed_tensors,
            bytes_delta_mb=result.bytes_delta_mb,
            heatmap_vec=result.heatmap_vec,
            out_path=result.out_path,
            snapshot_id=result.snapshot_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gguf/validate", response_model=ValidateResponse)
async def validate_model(req: ValidateRequest):
    """Validate a model against evaluation datasets."""
    try:
        metrics = surgeon.validate(
            req.model_path,
            req.dataset_path,
            req.cache_base
        )
        return ValidateResponse(
            ppl=metrics.ppl,
            acc=metrics.acc,
            drift=metrics.drift,
            guardrail=metrics.guardrail,
            logs=metrics.logs,
            passed=metrics.passes_gates()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gguf/sign", response_model=SignResponse)
async def sign_model(req: SignRequest):
    """Sign a model with provenance data."""
    try:
        checksum, signature = surgeon.embed_provenance(
            req.model_path,
            req.ops
        )
        return SignResponse(
            checksum=checksum,
            signature=signature
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gguf/commit")
async def commit_model(
    req: CommitRequest,
    background_tasks: BackgroundTasks
):
    """Commit model changes to disk."""
    try:
        # Run commit in background to avoid timeout
        background_tasks.add_task(
            surgeon.commit,
            req.model_path,
            req.require_gates
        )
        return {"status": "commit scheduled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))