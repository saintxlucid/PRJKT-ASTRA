import os, json, sys
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(r"X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)")
OUT = REPO_ROOT / "analysis"
EXCLUDES = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "htmlcov", "models", ".hf_cache", ".torch_cache", "node_modules", "logs", "data", "qdrant"}
TEXT_EXT = {".py", ".md", ".yaml", ".yml", ".json", ".toml", ".ini", ".txt", ".sh", ".ps1", ".bat", ".dockerfile"}

OUT.mkdir(exist_ok=True)

inv = {
    "scan_time": datetime.utcnow().isoformat() + "Z",
    "repo_root": str(REPO_ROOT),
    "dirs": {},
    "top_by_size": [],
    "top_by_loc": [],
    "summary": {"total_files": 0, "total_bytes": 0, "total_loc": 0}
}
index_path = OUT / "repo_index.jsonl"
inv_path = OUT / "repo_inventory.json"

index_f = index_path.open("w", encoding="utf-8")

def approx_loc(p: Path) -> int:
    try:
        if p.suffix.lower() in TEXT_EXT:
            with p.open("r", encoding="utf-8", errors="ignore") as f:
                return sum(1 for _ in f)
        return 0
    except Exception:
        return 0

print(f"Scanning {REPO_ROOT}...")
for root, dirs, files in os.walk(REPO_ROOT):
    # prune excludes
    dirs[:] = [d for d in dirs if d not in EXCLUDES]
    rel_dir = os.path.relpath(root, REPO_ROOT)
    if rel_dir == ".":
        rel_dir = ""
    dkey = rel_dir.replace("\\", "/")
    inv["dirs"].setdefault(dkey, {"files": 0, "bytes": 0, "loc": 0, "ext_counts": {}})
    for name in files:
        p = Path(root) / name
        try:
            st = p.stat()
        except Exception:
            continue
        size = int(st.st_size)
        loc = approx_loc(p)
        ext = p.suffix.lower() or "(no ext)"
        rec = {
            "path": str(p),
            "rel": str(p.relative_to(REPO_ROOT)).replace("\\", "/"),
            "ext": ext,
            "size": size,
            "loc": loc,
            "mtime": int(st.st_mtime)
        }
        index_f.write(json.dumps(rec) + "\n")
        # aggregate
        inv["dirs"][dkey]["files"] += 1
        inv["dirs"][dkey]["bytes"] += size
        inv["dirs"][dkey]["loc"] += loc
        inv["dirs"][dkey]["ext_counts"][ext] = inv["dirs"][dkey]["ext_counts"].get(ext, 0) + 1
        inv["summary"]["total_files"] += 1
        inv["summary"]["total_bytes"] += size
        inv["summary"]["total_loc"] += loc
        inv["top_by_size"].append((size, rec["rel"]))
        inv["top_by_loc"].append((loc, rec["rel"]))

index_f.close()
inv["top_by_size"] = [(s, f) for s, f in sorted(inv["top_by_size"], reverse=True)[:200]]
inv["top_by_loc"] = [(l, f) for l, f in sorted(inv["top_by_loc"], reverse=True)[:200]]

json.dump(inv, inv_path.open("w", encoding="utf-8"), indent=2)
print(f"Wrote {inv_path} ({inv['summary']['total_files']} files, {inv['summary']['total_loc']:,} LOC)")
print(f"Wrote {index_path}")
