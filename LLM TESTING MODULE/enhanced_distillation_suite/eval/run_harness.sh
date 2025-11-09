#!/usr/bin/env bash
set -euo pipefail

MODEL_PATH=${1:-models/phaseC}
TASKS=${2:-arc_easy,hellaswag,winogrande}
BS=${3:-8}

echo "[lm-eval] running on $MODEL_PATH tasks=$TASKS"
python -m lm_eval \
  --model hf \
  --model_args pretrained="$MODEL_PATH",dtype=float16 \
  --tasks "$TASKS" \
  --batch_size "$BS" \
  --log_samples \
  --output_path eval/outputs