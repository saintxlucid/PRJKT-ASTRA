import argparse, json
from transformers import AutoTokenizer
from collections import Counter

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--teacher", required=True, help="JSONL with fields: prompt, neox_output, (optional) teacher_tokens")
    ap.add_argument("--student", default="gpt2-large")
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(args.student)
    total, covered = 0, 0
    lengths = Counter()

    with open(args.teacher, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            txt = obj.get("neox_output", "")
            ids = tok(txt)["input_ids"]
            total += len(txt.split())
            covered += len(ids)
            lengths[len(ids)] += 1

    coverage = 100.0 * covered / max(total,1)
    print(f"[TokenMapAudit] Approx coverage (student tokens per word): {coverage:.2f}%")
    print("[Len histogram] (student tokenized sequence length counts):")
    for L, c in lengths.most_common(10):
        print(f"  {L}: {c}")

if __name__ == "__main__":
    main()