# Usage Guide: GPT-2 Knowledge Distillation Pipeline

This guide explains how to use the complete knowledge distillation pipeline to train a smaller GPT-2 model that mimics the behavior of a larger GPT-NeoX 20B model.

## Prerequisites

1. Python 3.8 or higher
2. GPU with at least 24GB VRAM (recommended for training)
3. At least 100GB of free disk space for datasets and model storage

## Installation

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. For GPU training, ensure you have CUDA-compatible PyTorch:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

## Pipeline Overview

The distillation pipeline consists of four main stages:

1. **Dataset Creation**: Generate responses from the teacher model (GPT-NeoX)
2. **Model Training**: Train the student model (GPT-2) on the generated dataset
3. **Evaluation**: Compare the performance of teacher and student models
4. **Analysis**: Calculate perplexity and other metrics

## Stage 1: Dataset Creation

Generate responses from the GPT-NeoX teacher model using your prompt dataset:

```bash
python scripts/generate_neox_outputs.py \
  --input_dataset data/sample_prompts.json \
  --output_dataset data/neox_distillation_dataset.json \
  --model_name EleutherAI/gpt-neox-20b \
  --max_new_tokens 256
```

### Custom Prompt Datasets

You can use your own prompt datasets in JSON or JSONL format:
- JSON format: Array of objects with a "prompt" field
- JSONL format: One JSON object per line with a "prompt" field

Example JSON format:
```json
[
  {
    "prompt": "Explain quantum entanglement in simple terms."
  },
  {
    "prompt": "Write a short poem about artificial intelligence."
  }
]
```

## Stage 2: Model Training

Train the GPT-2 student model using the generated dataset:

```bash
python scripts/train_gpt2_distilled.py \
  --dataset_path data/neox_distillation_dataset.json \
  --output_dir models/gpt2-distilled \
  --model_name gpt2-large \
  --per_device_train_batch_size 2 \
  --gradient_accumulation_steps 8 \
  --learning_rate 3e-5 \
  --num_train_epochs 3 \
  --fp16
```

### Training Configuration Options

- `--model_name`: Choose from "gpt2", "gpt2-medium", "gpt2-large", or "gpt2-xl"
- `--per_device_train_batch_size`: Adjust based on your GPU memory (lower for less memory)
- `--gradient_accumulation_steps`: Increase if you need larger effective batch sizes
- `--learning_rate`: Typical values are between 1e-5 and 5e-5
- `--fp16`: Enable mixed precision training for faster training and lower memory usage

## Stage 3: Model Evaluation

Compare outputs from the teacher and student models:

```bash
python scripts/evaluate_models.py \
  --test_prompts data/sample_prompts.json \
  --teacher_model EleutherAI/gpt-neox-20b \
  --student_model models/gpt2-distilled \
  --output_file model_comparison.json
```

## Stage 4: Perplexity Calculation

Calculate perplexity to quantify model performance:

```bash
python scripts/calculate_perplexity.py \
  --test_dataset data/neox_distillation_dataset.json \
  --model_path models/gpt2-distilled
```

## Advanced Distillation Techniques

### Soft Target Loss

The training script supports knowledge distillation with soft targets using KL divergence:

```bash
python scripts/train_gpt2_distilled.py \
  --dataset_path data/neox_distillation_dataset.json \
  --output_dir models/gpt2-distilled-advanced \
  --model_name gpt2-large \
  --distillation_alpha 0.7 \
  --temperature 3.0
```

Parameters:
- `--distillation_alpha`: Weight for distillation loss (0.0 = only CE loss, 1.0 = only distillation loss)
- `--temperature`: Temperature for softening probability distributions (higher = softer)

## Running the Complete Pipeline

### Windows:
```cmd
run_distillation.bat
```

### Linux/macOS:
```bash
chmod +x run_distillation.sh
./run_distillation.sh
```

## Monitoring Training Progress

Training logs are saved to:
- Console output during training
- TensorBoard logs in the `logs/` directory
- Checkpoints saved in the `output_dir` during training

To view TensorBoard logs:
```bash
tensorboard --logdir models/gpt2-distilled/logs
```

## Troubleshooting

### Out of Memory Errors

If you encounter CUDA out of memory errors:
1. Reduce `--per_device_train_batch_size`
2. Increase `--gradient_accumulation_steps` to maintain effective batch size
3. Enable `--fp16` for mixed precision training
4. Use a smaller GPT-2 variant (gpt2 or gpt2-medium instead of gpt2-large)

### Slow Generation

For faster dataset creation:
1. Use a quantized version of GPT-NeoX if available
2. Reduce `--max_new_tokens` for shorter responses
3. Use GPU inference if available

### Model Quality Issues

To improve distilled model quality:
1. Increase the size of the training dataset
2. Train for more epochs
3. Experiment with different learning rates
4. Use advanced distillation techniques (soft targets, temperature scaling)

## Customization

### Adding New Prompt Sources

1. Create a new JSON/JSONL file with your prompts
2. Use the `generate_neox_outputs.py` script to create responses
3. Train the model on the new dataset

### Modifying Training Process

The training script can be customized by modifying:
- Loss functions in `DistillationTrainer`
- Data preprocessing in `tokenize_function`
- Training arguments in `TrainingArguments`

## Performance Optimization

### For Limited Hardware

1. Use smaller GPT-2 models (gpt2 or gpt2-medium)
2. Reduce batch sizes and sequence lengths
3. Use gradient accumulation for larger effective batch sizes
4. Enable mixed precision training with `--fp16`

### For Maximum Performance

1. Use multiple GPUs with `--n_gpu` parameter
2. Enable DeepSpeed optimization for very large models
3. Use optimized CUDA kernels
4. Increase batch sizes within memory constraints

## Expected Results

After successful training, you should have:
- A distilled GPT-2 model that mimics GPT-NeoX behavior
- Model checkpoints saved in the output directory
- Training logs and metrics
- Lower perplexity compared to untrained GPT-2 models

The distilled model will be significantly smaller and faster than GPT-NeoX while retaining much of its knowledge and capabilities.