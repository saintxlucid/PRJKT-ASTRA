import argparse, json, math, hashlib
from typing import List, Dict, Tuple, Iterable

def shingles(text: str, k: int = 8) -> set:
    t = text.lower()
    return { t[i:i+k] for i in range(max(0, len(t)-k+1)) }

def jaccard(a: set, b: set) -> float:
    if not a and not b: return 1.0
    return len(a & b) / max(1, len(a | b))

def hash_shingle_set(s: set) -> str:
    h = hashlib.sha1()
    for token in sorted(s):
        h.update(token.encode("utf-8"))
    return h.hexdigest()

def load_jsonl(path: str) -> Iterable[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def save_jsonl(path: str, rows: Iterable[Dict]):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def filter_near_dups(rows: List[Dict], text_key: str, jaccard_thresh: float = 0.9, k: int = 8) -> List[Dict]:
    seen = {}
    out = []
    for r in rows:
        txt = r.get(text_key, "") or ""
        s = shingles(txt, k=k)
        sig = hash_shingle_set(s)
        dup = False
        # quick exact-sig gate
        if sig in seen:
            dup = True
        else:
            # lightweight jaccard compare against recent signatures (windowed)
            # for simplicity we just store a few
            for _sig, _s in list(seen.items())[-256:]:
                if jaccard(s, _s) >= jaccard_thresh:
                    dup = True
                    break
        if not dup:
            seen[sig] = s
            out.append(r)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_jsonl", required=True)
    ap.add_argument("--out_jsonl", required=True)
    ap.add_argument("--text_key", default="neox_output")
    ap.add_argument("--jaccard_thresh", type=float, default=0.9)
    ap.add_argument("--k", type=int, default=8)
    args = ap.parse_args()

    rows = list(load_jsonl(args.in_jsonl))
    filtered = filter_near_dups(rows, args.text_key, args.jaccard_thresh, args.k)
    save_jsonl(args.out_jsonl, filtered)
    print(f"[data_filter] kept {len(filtered)} / {len(rows)} after near-dup filtering (Jaccard>={args.jaccard_thresh}).")

if __name__ == "__main__":
    main()