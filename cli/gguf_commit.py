#!/usr/bin/env python3
"""
GGUF Model Commit CLI - Signs and commits evolved models

Handles model signing and committing with optional canary flag.
Uses the FastAPI service to ensure consistency with modal behavior.
"""

import argparse
import json
import os
import requests
from typing import Dict, Any

def load_meta(meta_arg: str) -> Dict[str, Any]:
    """Load metadata from JSON string or file"""
    try:
        if os.path.exists(meta_arg):
            return json.load(open(meta_arg, "r", encoding="utf-8"))
        return json.loads(meta_arg)
    except Exception:
        return {"note": meta_arg}

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Sign and commit evolved GGUF models"
    )
    ap.add_argument("--out", required=True,
                   help="Path to model file to sign and commit")
    ap.add_argument("--meta", default="{}",
                   help="JSON string or path to JSON metadata")
    ap.add_argument("--service", default="http://127.0.0.1:8765",
                   help="ASTRA Evolution service URL")
    ap.add_argument("--canary", action="store_true",
                   help="Mark as canary release")

    args = ap.parse_args()

    # Load metadata
    meta = load_meta(args.meta)

    try:
        # Sign the model
        sign_resp = requests.post(
            f"{args.service}/gguf/sign",
            json={"outPath": args.out, "meta": meta},
            timeout=60
        )
        sign_resp.raise_for_status()
        print(json.dumps({"sign": sign_resp.json()}, indent=2))

        # Commit the model
        commit_resp = requests.post(
            f"{args.service}/gguf/commit",
            json={"outPath": args.out, "requireCanary": args.canary},
            timeout=60
        )
        commit_resp.raise_for_status()
        print(json.dumps({"commit": commit_resp.json()}, indent=2))

    except requests.exceptions.RequestException as e:
        print(f"Error: Failed to sign/commit model: {str(e)}")
        raise SystemExit(1)

if __name__ == "__main__":
    main()