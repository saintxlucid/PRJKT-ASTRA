import os, sys, json
from pathlib import Path
import yaml
from typing import Any
from datasets import load_dataset, DatasetDict
import time

CFG = yaml.safe_load(Path("datasets.yaml").read_text())
CACHE_DIR = Path(CFG.get("cache_dir", "./cache"))
OUT_DIR   = Path(CFG.get("output_dir", "./data"))
DATASETS  = CFG.get("datasets", [])

# Keep HF cache local & reproducible
os.environ["HF_DATASETS_CACHE"] = str(CACHE_DIR.resolve())


def save(ds: DatasetDict, out_dir: Path) -> None:
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    ds.save_to_disk(str(out_dir))


def enhanced_try_load(name: str, config: str | None = None, split: str | None = None, retries: int = 3) -> Any:
    """Enhanced dataset loader with retries and error handling."""
    alts = [name]
    if name.lower() in {"docvqa/funsd", "funsd"}:
        alts = ["docvqa/funsd", "nielsr/funsd"]

    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        for nm in alts:
            try:
                if config:
                    return load_dataset(nm, config, split=split)
                return load_dataset(nm, split=split)
            except Exception as e:
                last_err = e
                print(f"[Retry {attempt}/{retries}] Failed to load {nm}: {e}")
                time.sleep(2)  # Backoff before retry
    assert last_err is not None
    raise last_err


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[ASTRA] Cache: {CACHE_DIR.resolve()}\n[ASTRA] Output: {OUT_DIR.resolve()}")

    pulled: list[dict[str, str | None]] = []
    for item in DATASETS:
        name   = item["name"]
        config = item.get("config")
        split  = item.get("split", "train")
        target = OUT_DIR / name.replace("/", "__")
        try:
            print(f"\n[ASTRA] Pulling: {name} | config={config} | split={split}")
            ds = enhanced_try_load(name, config, split)
            # Normalize to DatasetDict for save_to_disk parity
            if not isinstance(ds, DatasetDict):
                ds = DatasetDict({"data": ds})
            save(ds, target)
            print(f"[OK] Saved → {target}")
            pulled.append({"name": name, "config": config, "split": split, "path": str(target)})
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] {name} :: {e}")

    manifest = OUT_DIR / "_manifest.json"
    manifest.write_text(json.dumps({"datasets": pulled}, indent=2))
    print(f"\n[ASTRA] Manifest written → {manifest}")


if __name__ == "__main__":
    main()
