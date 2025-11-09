#!/bin/bash

# Shell script to run the complete GPT-2 distillation pipeline

echo "========================================"
echo "GPT-2 Knowledge Distillation Pipeline"
echo "========================================"

# Check if Python is installed
if ! command -v python3 &> /dev/null
then
    echo "Error: Python3 is not installed"
    exit 1
fi

# Create directories if they don't exist
mkdir -p data models logs

echo "1. Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error installing dependencies"
    exit 1
fi

echo "2. Generating dataset with GPT-NeoX responses..."
python3 scripts/generate_neox_outputs.py \
  --input_dataset data/sample_prompts.json \
  --output_dataset data/neox_distillation_dataset.json \
  --model_name EleutherAI/gpt-neox-20b \
  --max_new_tokens 256

if [ $? -ne 0 ]; then
    echo "Error generating dataset"
    exit 1
fi

echo "3. Training GPT-2 student model..."
python3 scripts/train_gpt2_distilled.py \
  --dataset_path data/neox_distillation_dataset.json \
  --output_dir models/gpt2-distilled \
  --model_name gpt2-large \
  --per_device_train_batch_size 2 \
  --gradient_accumulation_steps 8 \
  --learning_rate 3e-5 \
  --num_train_epochs 3 \
  --fp16

if [ $? -ne 0 ]; then
    echo "Error training model"
    exit 1
fi

echo "4. Calculating model perplexity..."
python3 scripts/calculate_perplexity.py \
  --test_dataset data/neox_distillation_dataset.json \
  --model_path models/gpt2-distilled

if [ $? -ne 0 ]; then
    echo "Error calculating perplexity"
    exit 1
fi

echo "========================================"
echo "Distillation pipeline completed successfully!"
echo "Trained model saved to models/gpt2-distilled"
echo "========================================"