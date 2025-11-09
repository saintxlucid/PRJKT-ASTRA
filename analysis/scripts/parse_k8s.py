import yaml, json
from pathlib import Path

REPO_ROOT = Path(r"X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)")
K8S = REPO_ROOT / "k8s"
OUT = REPO_ROOT / "analysis" / "k8s_index.json"

items = []
if K8S.exists():
    for yml in K8S.rglob("*.y*ml"):
        try:
            docs = list(yaml.safe_load_all(yml.read_text(encoding="utf-8", errors="ignore")))
            for d in docs:
                if not isinstance(d, dict):
                    continue
                items.append({
                    "file": str(yml.relative_to(REPO_ROOT)).replace("\\", "/"),
                    "kind": d.get("kind"),
                    "name": d.get("metadata", {}).get("name"),
                    "ns": d.get("metadata", {}).get("namespace"),
                    "spec_keys": list((d.get("spec") or {}).keys())
                })
        except Exception as e:
            items.append({"file": str(yml.relative_to(REPO_ROOT)).replace("\\", "/"), "error": str(e)})
else:
    print(f"K8s directory not found: {K8S}")

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(items, indent=2), encoding="utf-8")
print(f"Wrote {OUT} ({len(items)} K8s objects)")
