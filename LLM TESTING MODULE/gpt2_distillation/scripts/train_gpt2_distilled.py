"""
Script to train a GPT-2 model using knowledge distillation from GPT-NeoX outputs.
"""

import json
import argparse
from typing import Dict, Any
from datasets import Dataset
from transformers import (
    GPT2Tokenizer, 
    GPT2LMHeadModel, 
    Trainer, 
    TrainingArguments, 
    DataCollatorForLanguageModeling
)
import torch
from torch.nn import KLDivLoss
import torch.nn.functional as F

def tokenize_function(example: Dict[str, str], tokenizer, max_length: int = 1024) -> Dict[str, Any]:
    """
    Tokenize the prompt-response pairs for training.
    
    Args:
        example: Dictionary containing 'prompt' and 'neox_output'
        tokenizer: GPT-2 tokenizer
        max_length: Maximum sequence length
        
    Returns:
        Tokenized inputs with labels
    """
    # Format the input as instruction following
    full_text = f"### PROMPT:\n{example['prompt']}\n\n### RESPONSE:\n{example['neox_output']}"
    
    # Tokenize
    tokens = tokenizer(
        full_text, 
        truncation=True, 
        padding="max_length", 
        max_length=max_length,
        return_tensors="pt"
    )
    
    # Convert to regular tensors (remove batch dimension)
    tokens = {k: v.squeeze(0) for k, v in tokens.items()}
    
    # Labels are the same as input_ids for language modeling
    tokens["labels"] = tokens["input_ids"].clone()
    
    return tokens

def load_distillation_dataset(dataset_path: str, tokenizer, max_length: int = 1024) -> Dataset:
    """
    Load and preprocess the distillation dataset.
    
    Args:
        dataset_path: Path to the JSON dataset
        tokenizer: GPT-2 tokenizer
        max_length: Maximum sequence length
        
    Returns:
        Processed dataset ready for training
    """
    # Load dataset
    with open(dataset_path, 'r') as f:
        data = json.load(f)
    
    # Convert to HuggingFace dataset
    dataset = Dataset.from_list(data)
    
    # Tokenize dataset
    dataset = dataset.map(
        lambda example: tokenize_function(example, tokenizer, max_length),
        batched=False,
        remove_columns=dataset.column_names
    )
    
    return dataset

def load_config(config_path: str) -> dict:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    try:
        import yaml
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Warning: Could not load config file {config_path}: {e}")
        return {}

def merge_config_with_args(args, config: dict):
    """
    Merge configuration with command line arguments.
    
    Args:
        args: Parsed command line arguments
        config: Configuration dictionary
        
    Returns:
        Updated arguments
    """
    # Merge config with args (args take precedence)
    for key, value in config.items():
        if not hasattr(args, key) or getattr(args, key) is None:
            setattr(args, key, value)
        elif isinstance(getattr(args, key), dict) and isinstance(value, dict):
            # Merge nested dictionaries
            merged = getattr(args, key).copy()
            merged.update(value)
            setattr(args, key, merged)
    
    return args

def main():
    parser = argparse.ArgumentParser(description="Train GPT-2 with knowledge distillation")
    parser.add_argument("--dataset_path", type=str, required=True,
                        help="Path to the distillation dataset")
    parser.add_argument("--output_dir", type=str, default="./gpt2-distilled",
                        help="Directory to save the trained model")
    parser.add_argument("--model_name", type=str, default="gpt2-large",
                        help="Name/path of the student model")
    parser.add_argument("--config", type=str, 
                        help="Path to configuration YAML file")
    parser.add_argument("--max_length", type=int, default=1024,
                        help="Maximum sequence length")
    parser.add_argument("--per_device_train_batch_size", type=int, default=2,
                        help="Training batch size per device")
    parser.add_argument("--gradient_accumulation_steps", type=int, default=8,
                        help="Gradient accumulation steps")
    parser.add_argument("--learning_rate", type=float, default=3e-5,
                        help="Learning rate")
    parser.add_argument("--num_train_epochs", type=int, default=3,
                        help="Number of training epochs")
    parser.add_argument("--warmup_steps", type=int, default=100,
                        help="Number of warmup steps")
    parser.add_argument("--save_steps", type=int, default=500,
                        help="Save checkpoint every N steps")
    parser.add_argument("--logging_steps", type=int, default=10,
                        help="Log metrics every N steps")
    parser.add_argument("--weight_decay", type=float, default=0.01,
                        help="Weight decay")
    parser.add_argument("--fp16", action="store_true",
                        help="Use mixed precision training")
    parser.add_argument("--distillation_alpha", type=float, default=0.5,
                        help="Weight for distillation loss (0.0 = only CE loss)")
    parser.add_argument("--temperature", type=float, default=2.0,
                        help="Temperature for softening probability distributions")
    parser.add_argument("--lora", type=dict, default=None,
                        help="LoRA configuration")
    parser.add_argument("--loss_weights", type=dict, default=None,
                        help="Loss weights configuration")
    parser.add_argument("--sched", type=dict, default=None,
                        help="Scheduler configuration")
    
    args = parser.parse_args()
    
    # Load configuration if provided
    if args.config:
        config = load_config(args.config)
        args = merge_config_with_args(args, config)
    
    # Load tokenizer and model
    tokenizer = GPT2Tokenizer.from_pretrained(args.model_name)
    tokenizer.pad_token = tokenizer.eos_token
    
    model = GPT2LMHeadModel.from_pretrained(args.model_name)
    
    # Apply LoRA if configured
    if args.lora and args.lora.get("enabled", False):
        try:
            from peft import get_peft_model, LoraConfig, TaskType
            
            lora_config = LoraConfig(
                r=args.lora.get("r", 8),
                lora_alpha=args.lora.get("alpha", 32),
                target_modules=args.lora.get("target_modules", ["c_attn", "c_proj"]),
                lora_dropout=args.lora.get("dropout", 0.05),
                bias="none",
                task_type=TaskType.CAUSAL_LM
            )
            
            model = get_peft_model(model, lora_config)
            print("LoRA enabled")
            model.print_trainable_parameters()
        except ImportError:
            print("Warning: LoRA requested but 'peft' package not available")
    
    # Load dataset
    dataset = load_distillation_dataset(args.dataset_path, tokenizer, args.max_length)
    print(f"Loaded dataset with {len(dataset)} examples")
    
    # Setup training arguments
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        warmup_steps=args.warmup_steps,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_strategy="steps",
        num_train_epochs=args.num_train_epochs,
        weight_decay=args.weight_decay,
        fp16=args.fp16,
        report_to="none",  # Disable wandb/tensorboard
        logging_dir=f"{args.output_dir}/logs",
        save_total_limit=2,  # Keep only last 2 checkpoints
        dataloader_pin_memory=False,  # Reduce memory usage
        # Scheduler configuration
        lr_scheduler_type=args.sched.get("type", "linear") if args.sched else "linear",
    )
    
    # Setup trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )
    
    # Start training
    print("Starting training...")
    trainer.train()
    
    # Save final model
    trainer.save_model()
    tokenizer.save_pretrained(args.output_dir)
    print(f"Model saved to {args.output_dir}")

if __name__ == "__main__":
    main()