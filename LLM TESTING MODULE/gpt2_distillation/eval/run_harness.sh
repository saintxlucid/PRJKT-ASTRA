#!/bin/bash

# Evaluation harness script
# Runs automated evaluation suite on trained models

echo "========================================"
echo "Running Evaluation Harness"
echo "========================================"

# Check if model path is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <model_path>"
    echo "Example: $0 models/gpt2-distilled"
    exit 1
fi

MODEL_PATH=$1
MODEL_NAME=$(basename $MODEL_PATH)

# Create results directory
mkdir -p artifacts/reports/$(date +%Y%m%d)_${MODEL_NAME}

echo "Evaluating model: $MODEL_PATH"

# Run perplexity evaluation
echo "1. Running perplexity evaluation..."
python scripts/calculate_perplexity.py \
  --test_dataset data/sample_prompts.json \
  --model_path $MODEL_PATH \
  --model_type gpt2

# Run lm-evaluation-harness tasks if available
if command -v lm_eval &> /dev/null; then
    echo "2. Running lm-evaluation-harness tasks..."
    lm_eval \
      --model hf \
      --model_args pretrained=$MODEL_PATH \
      --tasks arc,hellaswag,winogrande,gsm8k \
      --num_fewshot 0 \
      --batch_size 4 \
      --output_path artifacts/reports/$(date +%Y%m%d)_${MODEL_NAME}/lm_eval.json
else
    echo "Warning: lm-evaluation-harness not found, skipping tasks"
fi

# Run latency benchmarks
echo "3. Running latency benchmarks..."
python eval/benchmark_latency.py \
  --model_path $MODEL_PATH \
  --batch_sizes 1,2,4 \
  --sequence_lengths 128,256,512

# Run toxicity checks
echo "4. Running toxicity checks..."
python eval/check_safety.py \
  --model_path $MODEL_PATH \
  --test_prompts data/safety_prompts.jsonl

echo "========================================"
echo "Evaluation complete!"
echo "Results saved to: artifacts/reports/$(date +%Y%m%d)_${MODEL_NAME}"
echo "========================================"