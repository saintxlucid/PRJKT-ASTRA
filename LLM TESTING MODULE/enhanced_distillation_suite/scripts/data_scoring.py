import argparse, json, math, random, sys

def entropy_from_topk(probs):
    # probs: list of floats summing to ~1.0
    return -sum(p*math.log(p+1e-12) for p in probs)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_jsonl", required=True, help="Teacher outputs with topk probs: {topk_probs: [..]}")
    ap.add_argument("--out_jsonl", required=True)
    ap.add_argument("--a", type=float, default=0.5)
    ap.add_argument("--b", type=float, default=0.8)
    ap.add_argument("--minw", type=float, default=0.3)
    ap.add_argument("--maxw", type=float, default=1.5)
    args = ap.parse_args()

    with open(args.in_jsonl, "r", encoding="utf-8") as fin, open(args.out_jsonl, "w", encoding="utf-8") as fout:
        for line in fin:
            obj = json.loads(line)
            topk = obj.get("topk_probs", None)
            H = entropy_from_topk(topk) if topk else 0.0
            w = max(args.minw, min(args.maxw, args.a + args.b*H))
            obj["entropy"] = H
            obj["weight"] = w
            fout.write(json.dumps(obj, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    main()