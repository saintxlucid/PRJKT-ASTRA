@echo off
REM Batch script to run the complete GPT-2 distillation pipeline

echo ========================================
echo GPT-2 Knowledge Distillation Pipeline
echo ========================================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    exit /b 1
)

REM Create directories if they don't exist
if not exist "data" mkdir data
if not exist "models" mkdir models
if not exist "logs" mkdir logs

echo 1. Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error installing dependencies
    exit /b 1
)

echo 2. Generating dataset with GPT-NeoX responses...
python scripts/generate_neox_outputs.py ^
  --input_dataset data/sample_prompts.json ^
  --output_dataset data/neox_distillation_dataset.json ^
  --model_name EleutherAI/gpt-neox-20b ^
  --max_new_tokens 256

if %errorlevel% neq 0 (
    echo Error generating dataset
    exit /b 1
)

echo 3. Training GPT-2 student model...
python scripts/train_gpt2_distilled.py ^
  --dataset_path data/neox_distillation_dataset.json ^
  --output_dir models/gpt2-distilled ^
  --model_name gpt2-large ^
  --per_device_train_batch_size 2 ^
  --gradient_accumulation_steps 8 ^
  --learning_rate 3e-5 ^
  --num_train_epochs 3 ^
  --fp16

if %errorlevel% neq 0 (
    echo Error training model
    exit /b 1
)

echo 4. Calculating model perplexity...
python scripts/calculate_perplexity.py ^
  --test_dataset data/neox_distillation_dataset.json ^
  --model_path models/gpt2-distilled

if %errorlevel% neq 0 (
    echo Error calculating perplexity
    exit /b 1
)

echo ========================================
echo Distillation pipeline completed successfully!
echo Trained model saved to models/gpt2-distilled
echo ========================================