"""
Model verification for ASTRA Core

Ensures the GPT-OSS model is present and readable.
"""

import os
import sys
import hashlib
import json

MODEL = "astra-local/data/models/gpt-oss-20b.Q4_K_M.gguf"

# Check alternative location if first one doesn't exist
if not os.path.exists(MODEL):
    MODEL = "models/gpt-oss-20b-q4_k_m.gguf"

if not os.path.exists(MODEL):
    print(json.dumps({"status": "missing", "path_checked": MODEL}))
    sys.exit(1)

size = os.path.getsize(MODEL) / 1e9
sha = hashlib.sha256(open(MODEL, "rb").read(65536)).hexdigest()

print(json.dumps({"status": "ok", "size_gb": round(size, 2), "sha": sha[:12]}))