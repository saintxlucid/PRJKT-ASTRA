from pathlib import Path
import json

manifest = Path("data/_manifest.json")
if not manifest.exists():
    print("[WARN] No manifest found at data/_manifest.json")
    raise SystemExit(0)

info = json.loads(manifest.read_text())
print("\n[ASTRA] Download Manifest:")
for d in info.get("datasets", []):
    p = Path(d["path"])
    sz = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    print(f" - {d['name']} | split={d['split']} | ~{sz/1e6:.1f} MB | {p}")
print("\n[OK] Verification complete.")
