#!/usr/bin/env python3
"""
GGUF Model Merge CLI - Interfaces with ASTRA Evolution Service

Merges LoRA adapters into base models with RoPE tuning and quantization options.
Uses the FastAPI service to ensure consistency with modal behavior.
"""

import argparse
import json
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional

def load_manifest(path: str) -> List[str]:
    """Load LoRA paths from manifest file"""
    data = json.load(open(path, "r", encoding="utf-8"))
    
    # Accept either {"id":{path,...}} or {"items":[{path:...}]}
    if isinstance(data, dict) and "items" in data:
        return [it["path"] for it in data["items"]]
    return [v["path"] for v in data.values()]

def main():
    ap = argparse.ArgumentParser(
        description="Merge LoRA adapters into GGUF models with RoPE tuning"
    )
    ap.add_argument("--base", required=True, 
                   help="Path to base GGUF model")
    ap.add_argument("--manifest", required=False,
                   help="Optional: adapters manifest JSON file")
    ap.add_argument("--out", required=True,
                   help="Output path for merged model")
    ap.add_argument("--rope-scale", type=float, default=1.0,
                   help="RoPE scaling factor (default: 1.0)")
    ap.add_argument("--rope-base", type=float, default=1e6,
                   help="RoPE base value (default: 1e6)")
    ap.add_argument("--quant", default=None,
                   help="Quantization format (e.g. Q5_K_M)")
    ap.add_argument("--repack", action="store_true",
                   help="Repack tensors for optimal layout")
    ap.add_argument("--service", default="http://127.0.0.1:8765",
                   help="ASTRA Evolution service URL")
    ap.add_argument("--preview", action="store_true",
                   help="Preview mode - don't write output file")

    args = ap.parse_args()

    # Load LoRA paths from manifest if provided
    loras: List[str] = []
    if args.manifest:
        loras = load_manifest(args.manifest)

    # Prepare request payload
    payload = {
        "basePath": args.base,
        "ops": {
            "quantize": args.quant,
            "loraPaths": loras,
            "ropeBase": args.rope_base,
            "ropeScale": args.rope_scale,
            "repack": args.repack
        },
        "preview": args.preview
    }

    # Call service endpoint
    try:
        r = requests.post(
            f"{args.service}/gguf/patch",
            json=payload,
            timeout=120
        )
        r.raise_for_status()
        res = r.json()

        # Override output path if specified
        if args.out and res.get("outPath") != args.out:
            res["outPath"] = args.out
            
        print(json.dumps(res, indent=2))
        
    except requests.exceptions.RequestException as e:
        print(f"Error: Failed to call evolution service: {str(e)}")
        raise SystemExit(1)

if __name__ == "__main__":
    main()