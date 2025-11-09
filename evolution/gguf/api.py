"""GGUF model patching and validation API."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from pathlib import Path

from .lora_merge import (
    GGUFModel,
    load_lora_gguf,
    merge_loras,
    validate_merge,
    preview_merge,
    embed_provenance
)

app = FastAPI()

class PatchRequest(BaseModel):
    """Request to patch a GGUF model."""
    base_path: str
    ops: Dict[str, dict] = {
        "lora_paths": List[str],
        "rope_base": Optional[float],
        "rope_scale": Optional[float], 
        "quantize": Optional[str],
        "repack": Optional[bool]
    }
    preview: bool = True

class PatchResponse(BaseModel):
    """Response from patch operation."""
    changed_tensors: int
    bytes_delta_mb: float
    heatmap_vec: List[float]
    out_path: str
    snapshot_id: str

class ValidateRequest(BaseModel):
    """Request to validate a patched model."""
    out_path: str
    dataset: str

class ValidateResponse(BaseModel):
    """Results of validation."""
    ppl: float
    acc: float
    drift: float
    logs: List[str]

class SignRequest(BaseModel):
    """Request to sign a model."""
    out_path: str
    meta: Dict[str, str]

class SignResponse(BaseModel):
    """Signing results."""
    checksum: str
    signature: str

@app.post("/gguf/patch", response_model=PatchResponse)
async def patch_model(req: PatchRequest):
    """Patch a GGUF model with LoRA adapters and other ops.
    
    Args:
        req: Patch request
        
    Returns:
        Patch results
    """
    try:
        # Load base model
        base = GGUFModel(req.base_path)
        
        # Load adapters
        adapters = []
        for path in req.ops.get("lora_paths", []):
            adapter = load_lora_gguf(path)
            adapters.append(adapter)
            
        # Preview merge
        preview = preview_merge(base, adapters)
        
        if req.preview:
            # Return preview only
            return PatchResponse(
                changed_tensors=preview.changed_tensors,
                bytes_delta_mb=preview.bytes_delta_mb,
                heatmap_vec=preview.heatmap_vec,
                out_path="",
                snapshot_id=preview.snapshot_id
            )
            
        # Perform actual merge
        merge_loras(base, adapters)
        
        # Apply RoPE tuning if requested
        if "rope_base" in req.ops or "rope_scale" in req.ops:
            base.kv_set("rope.freq_base", 
                       req.ops.get("rope_base", 10000.0))
            base.kv_set("rope.scale",
                       req.ops.get("rope_scale", 1.0))
            
        # Handle quantization
        if req.ops.get("quantize"):
            # TODO: Implement quantization
            pass
            
        # Embed provenance
        embed_provenance(base, adapters, preview)
        
        # Save output
        out_path = Path(req.base_path).with_suffix(".merged.gguf")
        base.save(str(out_path))
        
        return PatchResponse(
            changed_tensors=preview.changed_tensors,
            bytes_delta_mb=preview.bytes_delta_mb,
            heatmap_vec=preview.heatmap_vec,
            out_path=str(out_path),
            snapshot_id=preview.snapshot_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gguf/validate", response_model=ValidateResponse)
async def validate_model(req: ValidateRequest):
    """Validate a patched model.
    
    Args:
        req: Validation request
        
    Returns:
        Validation results
    """
    try:
        model = GGUFModel(req.out_path)
        results = validate_merge(model, req.dataset)
        
        return ValidateResponse(
            ppl=results.ppl_delta,
            acc=results.tool_accuracy,
            drift=results.drift,
            logs=results.logs
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gguf/sign", response_model=SignResponse) 
async def sign_model(req: SignRequest):
    """Sign a model with metadata.
    
    Args:
        req: Signing request
        
    Returns:
        Signature information
    """
    try:
        model = GGUFModel(req.out_path)
        
        # Load existing provenance
        provenance = model.kv_get("astra.signature")
        
        # Add metadata
        provenance.update(req.meta)
        
        # Update signature
        model.kv_set("astra.signature", provenance)
        model.save(req.out_path)
        
        return SignResponse(
            checksum=provenance["astra.checksum"],
            signature=provenance["astra.snapshot_id"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))