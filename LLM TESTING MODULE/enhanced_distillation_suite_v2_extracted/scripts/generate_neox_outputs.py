import argparse, json, time, requests, os, random
from typing import Dict, Any, Iterable

def load_prompts(path: str):
    if path.endswith(".jsonl"):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield json.loads(line).get("prompt", "")
    else:
        data = json.load(open(path, "r", encoding="utf-8"))
        if isinstance(data, list):
            for row in data:
                yield row.get("prompt", "")
        else:
            for row in data.get("data", []):
                yield row.get("prompt", "")

def call_vllm(prompt: str, host: str, topk: int, temperature: float, max_tokens: int) -> Dict[str, Any]:
    # Assumes vLLM OpenAI-compatible server
    url = host.rstrip("/") + "/v1/completions"
    payload = {
        "model": "neox-20b",
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "logprobs": topk,
        "echo": False
    }
    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    obj = r.json()
    choice = obj["choices"][0]
    out = {
        "text": choice.get("text","").strip(),
        "top_logprobs": choice.get("logprobs", {}).get("top_logprobs", [])
    }
    return out

def call_llamacpp(prompt: str, host: str, topk: int, temperature: float, max_tokens: int) -> Dict[str, Any]:
    # Assumes llama.cpp server at /completion endpoint
    url = host.rstrip("/") + "/completion"
    payload = {
        "prompt": prompt,
        "n_predict": max_tokens,
        "temperature": temperature,
        "logit_bias": {},
        "top_k": 50,
        "top_p": 0.95,
        "stop": []
    }
    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    obj = r.json()
    text = obj.get("content","") if isinstance(obj, dict) else ""
    # llama.cpp server may not expose top-k logits; we emit None
    return {"text": text, "top_logprobs": None}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True, help="path to JSON/JSONL with 'prompt' field or glob handled by shell")
    ap.add_argument("--out", required=True, help="output JSONL")
    ap.add_argument("--server", choices=["vllm","llama.cpp"], default="vllm")
    ap.add_argument("--host", default="http://127.0.0.1:8000")
    ap.add_argument("--emit-logits", action="store_true")
    ap.add_argument("--topk", type=int, default=50)
    ap.add_argument("--temperature", type=float, default=1.3)
    ap.add_argument("--max_tokens", type=int, default=256)
    args = ap.parse_args()

    prompts = list(load_prompts(args.prompts))
    with open(args.out, "w", encoding="utf-8") as fout:
        for p in prompts:
            if not p: 
                continue
            if args.server == "vllm":
                res = call_vllm(p, args.host, args.topk if args.emit_logits else 0, args.temperature, args.max_tokens)
            else:
                res = call_llamacpp(p, args.host, args.topk if args.emit_logits else 0, args.temperature, args.max_tokens)

            row = {
                "prompt": p,
                "neox_output": res.get("text",""),
                "temperature": args.temperature
            }
            if args.emit_logits and res.get("top_logprobs") is not None:
                # convert logprobs maps into topk_probs list per token (approximate)
                topk_probs = []
                for step in res["top_logprobs"]:
                    if isinstance(step, dict):
                        # Already {token: logprob}
                        probs = [float(v) for v in step.values()]
                    else:
                        probs = []
                    topk_probs.append(probs)
                row["topk_probs"] = topk_probs

            fout.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[generate_neox_outputs] wrote -> {args.out} ({len(prompts)} rows)")

if __name__ == "__main__":
    main()