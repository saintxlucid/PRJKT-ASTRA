"""Build Mini Corpora

Generate compact JSONL files from datasets for quick testing.
Offline-only: loads from local disk, exports to ./corpora/

Created: October 18, 2025
"""

from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Iterable, Tuple

from .dataset_loader import load_normalized
from .schema import Record


# ---- Configuration ----

OUT = Path(os.getenv("ASTRA_CORPUS_DIR", "./corpora")).resolve()

# Dataset targets: (name, record_limit)
TARGETS: list[Tuple[str, int]] = [
    ("google/speech_commands", 500),        # Wake-word / Keyword spotting
    ("openslr/librispeech_asr", 200),       # ASR sanity check
    ("contemmcm/clinc150", 1000),           # NLU intents
    ("PolyAI/banking77", 1000),             # NLU intents (banking domain)
    ("ag_news", 500),                       # Text classification
    ("imdb", 500),                          # Sentiment analysis
    ("docvqa/funsd", 200),                  # Forms/GUI OCR
    ("allenai/real-toxicity-prompts", 1000),  # Safety/toxicity detection
    ("mbpp", 100),                          # Code eval smoke test
    ("squad", 500),                         # QA baseline
    ("wikitext", 500),                      # Language modeling
    ("snips_built_in_intents", 300),        # Intent classification
]


# ---- Mini-Corpus Writer ----

def write_jsonl(path: Path, recs: Iterable[Record]) -> int:
    """
    Write records to JSONL file.
    
    Args:
        path: Output file path
        recs: Iterable of Record dicts
        
    Returns:
        Number of records written
    """
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
            count += 1
    return count


# ---- Main ----

def main():
    """Build all mini-corpora from datasets"""
    OUT.mkdir(parents=True, exist_ok=True)
    
    print(f"[ASTRA] Building mini-corpora in {OUT}")
    print(f"[*] Datasets: {len(TARGETS)}")
    print()
    
    total_records = 0
    
    for name, limit in TARGETS:
        key = name.replace("/", "__")
        out_path = OUT / f"{key}.jsonl"
        
        try:
            print(f"[*] {name:40s} → {key:40s} (limit={limit})")
            
            records = load_normalized(name, limit=limit)
            count = write_jsonl(out_path, records)
            total_records += count
            
            size_kb = out_path.stat().st_size / 1024
            print(f"    ✓ {count:5d} records | {size_kb:7.1f} KB\n")
            
        except Exception as e:
            print(f"    ✗ Error: {e}\n")
            continue
    
    print(f"[OK] Mini-corpora complete")
    print(f"     Total: {total_records} records")
    print(f"     Output: {OUT}")


if __name__ == "__main__":
    main()
