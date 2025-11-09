import argparse, time, torch
from transformers import AutoTokenizer, AutoModelForCausalLM

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--text", default="The quick brown fox jumps over the lazy dog.")
args = ap.parse_args()

tok = AutoTokenizer.from_pretrained(args.model)
if tok.pad_token is None: tok.pad_token = tok.eos_token
m = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.float16, device_map="auto")
enc = tok(args.text, return_tensors="pt").to(m.device)

with torch.inference_mode():
    t0 = time.time()
    out = m(**enc, labels=enc["input_ids"])
    t1 = time.time()
    ppl = torch.exp(out.loss).item()
    print(f"PPL={ppl:.3f} | fwd_time={t1-t0:.3f}s")