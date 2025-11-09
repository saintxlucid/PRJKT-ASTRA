# Enhanced GPT-2 Distillation Suite

Drop-in advanced configs and utilities for distilling GPT-2 (student) from GPT-NeoX 20B (teacher).

## Quickstart
```bash
pip install -r requirements.txt

# Phase A (warmup)
make phaseA

# Phase B (core)
make phaseB

# Phase C (sharpen)
make phaseC
```

## Notes
Provide your mixed datasets in data/*.jsonl with fields at least: prompt, neox_output.

Integrate teacher logits/top-k if available and adapt training/losses.py + train script.