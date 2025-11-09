import argparse, json, yaml, os, math
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments, DataCollatorForLanguageModeling
from datasets import load_dataset, Dataset, concatenate_datasets
import torch
from training.losses import mix_losses

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
        weight = float(m.get("weight",1.0))
        ds = ds.add_column("sample_weight", [weight]*len(ds))
        ds_list.append(ds)
    return concatenate_datasets(ds_list) if ds_list else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
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

    # Custom loss via Trainer override (simple hook)
    from transformers import Trainer
    class DistillTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            labels = inputs.get("labels")
            outputs = model(**{k:v for k,v in inputs.items() if k!="labels"})
            logits_s = outputs.logits
            # teacher logits not provided in this minimal example; use CE only
            loss = mix_losses(logits_s, None, labels, loss_weights, T, extras=None)
            return (loss, outputs) if return_outputs else loss

    trainer = DistillTrainer(
        model=model,
        args=args_train,
        train_dataset=ds_tok,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )
    trainer.train()

if __name__ == "__main__":
    main()