"""
ASTRA Model Verification - Supply Chain Security

Verifies SHA256 checksums of all models in security/models_registry.yaml
to detect tampering, corruption, or unauthorized model swaps.

Usage:
    python security/verify_models.py --write   # Populate checksums once
    python security/verify_models.py           # Verify integrity (run on boot)

Returns:
    Exit code 0: All models verified OK
    Exit code 1: Failures detected (missing files, checksum mismatches)
"""

import argparse
import hashlib
import json
import os
import sys
import yaml

REG_FILE = os.path.join("security", "models_registry.yaml")


def sha256_file(path: str) -> str:
    """Compute SHA256 hash of file in 1MB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description="Verify model integrity via SHA256")
    ap.add_argument("--write", action="store_true", 
                   help="Write missing sha256 hashes to registry")
    args = ap.parse_args()

    if not os.path.exists(REG_FILE):
        print(json.dumps({
            "verify_models": {
                "status": "FAIL",
                "issues": [f"Registry file not found: {REG_FILE}"]
            }
        }, indent=2))
        return 1

    with open(REG_FILE, "r", encoding="utf-8") as f:
        reg = yaml.safe_load(f)

    failures = []
    updated = False
    
    for m in reg.get("models", []):
        name = m.get("name", "unknown")
        path = m.get("path", "")
        
        if not path:
            failures.append(f"no path specified for {name}")
            continue
            
        if not os.path.exists(path):
            failures.append(f"missing: {path}")
            continue
            
        digest = sha256_file(path)
        
        if not m.get("sha256"):
            if args.write:
                m["sha256"] = digest
                updated = True
                print(f"✓ Computed SHA256 for {name}")
            else:
                failures.append(f"no checksum recorded for {path}")
        elif m["sha256"] != digest:
            failures.append(f"checksum mismatch: {path} (expected {m['sha256'][:16]}..., got {digest[:16]}...)")

    if args.write and updated:
        with open(REG_FILE, "w", encoding="utf-8") as f:
            yaml.safe_dump(reg, f, sort_keys=False)
        print(f"✓ Updated {REG_FILE} with checksums")

    if failures:
        print(json.dumps({
            "verify_models": {
                "status": "FAIL",
                "issues": failures
            }
        }, indent=2))
        return 1
        
    print(json.dumps({
        "verify_models": {
            "status": "OK",
            "verified": len(reg.get("models", []))
        }
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
