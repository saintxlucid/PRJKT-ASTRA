import argparse, torch
from transformers import AutoModelForCausalLM
from peft import PeftModel

ap = argparse.ArgumentParser()
ap.add_argument("--base", required=True, help="base student (e.g. gpt2-large)")
ap.add_argument("--lora_path", required=True, help="trained LoRA adapter path")
ap.add_argument("--out", required=True, help="output dir for merged model")
args = ap.parse_args()

base = AutoModelForCausalLM.from_pretrained(args.base)
lora = PeftModel.from_pretrained(base, args.lora_path)
merged = lora.merge_and_unload()
merged.save_pretrained(args.out)
print(f"[merge] saved merged weights to {args.out}")