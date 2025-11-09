import argparse, json, yaml, os, math
from typing import List, Dict, Any, Optional
from training.losses import mix_losses, kd_from_teacher_probs
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments, DataCollatorForLanguageModeling
from datasets import load_dataset, Dataset, concatenate_datasets
import torch

def load_mixes(mixes):
    ds_list = []
    for m in mixes:
        path = m["path"]
        if not os.path.exists(path):
            continue
        ext = os.path.splitext(path)[1]
        if ext == ".jsonl":
            ds = load_dataset("json", data_files=path, split="train")
        else:
            ds = Dataset.from_json(path)
        ds_list.append(ds)
    return concatenate_datasets(ds_list) if ds_list else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--teacher_logits_jsonl", default=None, help="JSONL aligned to training rows with field 'top_logprobs'")
    args = ap.parse_args()
    with open(args.config, "r") as f:
        cfg = yaml.safe_load(f)

    student_name = cfg.get("student_model", "gpt2-large")
    outdir = cfg.get("output_dir", "models/out")
    ctx = int(cfg.get("context_length", 1024))
    precision = cfg.get("precision", "fp16")
    T = float(cfg.get("temperature", 2.0))
    loss_weights = cfg.get("loss_weights", {"kd":0.6,"ce":0.3,"seq":0.05,"hint":0.05})
    grad_accum = int(cfg.get("grad_accum", 8))

    tokenizer = AutoTokenizer.from_pretrained(student_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(student_name)

    mixes = cfg.get("data", {}).get("mixes", [])
    ds = load_mixes(mixes)
    if ds is None:
        raise SystemExit("No datasets found. Please provide valid paths in configs.")

    def tok_fn(ex):
        txt = ex.get("neox_output") or ex.get("response") or ex.get("text") or ""
        prompt = ex.get("prompt","")
        full = f"### PROMPT:\n{prompt}\n\n### RESPONSE:\n{txt}"
        out = tokenizer(full, truncation=True, padding="max_length", max_length=ctx)
        out["labels"] = out["input_ids"].copy()
        return out

    ds_tok = ds.map(tok_fn, batched=False, remove_columns=[c for c in ds.column_names if c not in []])

    # after ds_tok creation, if teacher logits provided, align and cache sparse maps
    teacher_sparse: Optional[List[List[Dict[int,float]]]] = None
    if args.teacher_logits_jsonl:
        from scripts.utils_teacher_map import build_sparse_teacher_over_student
        import json
        tok_encode = lambda s: tokenizer.encode(s, add_special_tokens=False)
        teacher_sparse = []
        with open(args.teacher_logits_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                steps = obj.get("top_logprobs", [])
                row_sparse = []
                for step in steps:
                    row_sparse.append(build_sparse_teacher_over_student(step, tok_encode))
                teacher_sparse.append(row_sparse)

    args_train = TrainingArguments(
        output_dir=outdir,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=grad_accum,
        learning_rate=cfg.get("optimizer",{}).get("lr",2e-5),
        weight_decay=cfg.get("optimizer",{}).get("wd",0.1),
        logging_steps=20,
        save_steps=1000,
        num_train_epochs=1,
        fp16=(precision=="fp16"),
        bf16=(precision=="bf16"),
        report_to="none"
    )

    trainer = Trainer(
        model=model,
        args=args_train,
        train_dataset=ds_tok,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )
    trainer.train()

if __name__ == "__main__":
    main()