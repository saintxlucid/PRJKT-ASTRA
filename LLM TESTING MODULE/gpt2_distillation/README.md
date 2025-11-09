# GPT-2 Knowledge Distillation from GPT-NeoX 20B

This project implements knowledge distillation from a large GPT-NeoX 20B model to a smaller, more efficient GPT-2 model. The goal is to create a compact student model that retains much of the teacher model's capabilities.

## 🧠 Project Overview

Knowledge distillation is a technique where a smaller "student" model is trained to replicate the behavior of a larger "teacher" model. This project specifically focuses on distilling the knowledge from GPT-NeoX 20B (teacher) into GPT-2 (student).

## 📁 Project Structure

```
gpt2_distillation/
├── data/
│   └── sample_prompts.json          # Sample prompts for dataset creation
├── scripts/
│   ├── generate_neox_outputs.py     # Generate teacher model responses
│   ├── train_gpt2_distilled.py      # Train student model with distillation
│   ├── evaluate_models.py           # Compare teacher and student model outputs
│   ├── calculate_perplexity.py      # Calculate model perplexity
│   └── dataset_utils.py             # Utilities for dataset management
├── models/
│   └── gpt2-distilled/              # Trained student models (created during training)
├── logs/
│   └── training_log.txt             # Training logs (created during training)
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## ⚙️ Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. (Optional) For GPU training, install CUDA-compatible PyTorch:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## 🚀 Usage

### Phase 1: Dataset Creation

First, generate responses from the GPT-NeoX teacher model:

```bash
python scripts/generate_neox_outputs.py \
  --input_dataset data/sample_prompts.json \
  --output_dataset data/neox_distillation_dataset.json \
  --model_name EleutherAI/gpt-neox-20b \
  --max_new_tokens 256
```

### Phase 1.5: Dataset Management (Optional)

You can use the dataset utilities to analyze, filter, or split your dataset:

```bash
# Analyze dataset statistics
python -c "from scripts.dataset_utils import load_json_dataset, analyze_dataset; \
           data = load_json_dataset('data/neox_distillation_dataset.json'); \
           stats = analyze_dataset(data); \
           print(stats)"
```

### Phase 2: Model Training

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

## 🧪 Advanced Distillation Options

The training script supports several advanced distillation techniques:

- **Soft Target Loss**: Use KL divergence between teacher and student logits
- **Temperature Scaling**: Control the softness of probability distributions
- **Loss Weighting**: Balance between hard labels and soft targets

Example with advanced options:
```bash
python scripts/train_gpt2_distilled.py \
  --dataset_path data/neox_distillation_dataset.json \
  --output_dir models/gpt2-distilled-advanced \
  --model_name gpt2-large \
  --distillation_alpha 0.7 \
  --temperature 3.0 \
  --per_device_train_batch_size 1 \
  --gradient_accumulation_steps 16 \
  --learning_rate 2e-5
```

## 🔍 Evaluation

After training, evaluate your distilled model:

```python
from transformers import GPT2Tokenizer, GPT2LMHeadModel

# Load the distilled model
tokenizer = GPT2Tokenizer.from_pretrained("models/gpt2-distilled")
model = GPT2LMHeadModel.from_pretrained("models/gpt2-distilled")

# Generate text
input_text = "Explain quantum entanglement"
inputs = tokenizer(input_text, return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=100)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

## 🧬 Future Improvements

1. **Progressive Distillation**: Distill from GPT-NeoX → Mistral 7B → GPT-2
2. **Domain Adaptation**: Train on domain-specific datasets
3. **Advanced Loss Functions**: Implement hidden state matching or attention transfer
4. **Multi-stage Training**: Start with smaller models and gradually increase complexity

## 📚 References

- Hinton, G., Vinyals, O., & Dean, J. (2015). Distilling the knowledge in a neural network.
- Sanh, V., Debut, L., Chaumond, J., & Wolf, T. (2019). DistilBERT, a distilled version of BERT.