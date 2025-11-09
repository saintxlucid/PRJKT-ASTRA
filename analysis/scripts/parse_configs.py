import json, yaml, sys
from pathlib import Path

REPO_ROOT = Path(r"X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)")
OUT = REPO_ROOT / "analysis"
OUT.mkdir(exist_ok=True)

CONFIGS = [
    "config/config.yaml",
    "config/rag.yaml",
    "config/rag.json",
    "config/models_registry.yaml",
    "config/astra_identity.yaml",
    "config/astra_identity_v2.yaml",
    "config/autonomy_rules.yaml",
    "config/gates.yaml",
    "config/policy.yaml",
    "monitoring/config.yaml",
]

parsed = []
for rel in CONFIGS:
    p = REPO_ROOT / rel
    if not p.exists():
        print(f"Config not found: {rel}")
        continue
    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
        if p.suffix == ".json":
            obj = json.loads(content)
        else:
            obj = yaml.safe_load(content)
        out_file = OUT / (p.name + ".normalized.json")
        out_file.write_text(json.dumps(obj, indent=2), encoding="utf-8")
        parsed.append({"config": rel, "output": str(out_file.relative_to(REPO_ROOT)).replace("\\", "/")})
        print(f"Parsed {rel}")
    except Exception as e:
        print(f"Failed {rel}: {e}")

# Summary
(OUT / "config_parse_summary.json").write_text(json.dumps(parsed, indent=2), encoding="utf-8")
print(f"Config summary: {len(parsed)} configs parsed")
