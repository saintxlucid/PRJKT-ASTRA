"""
LoRA Integration for Distillation

This script implements LoRA (Low-Rank Adaptation) integration for efficient distillation
and fine-tuning of the GPT-2 student model.
"""

import argparse
import json
from typing import List, Dict, Any
from datasets import Dataset
from transformers import (
    GPT2Tokenizer, 
    GPT2LMHeadModel, 
    Trainer, 
    TrainingArguments,
    DataCollatorForLanguageModeling
)
import torch
from peft import get_peft_model, LoraConfig, TaskType

def tokenize_function(example: Dict[str, str], tokenizer, max_length: int = 1024) -> Dict[str, Any]:
    """
    Tokenize the prompt-response pairs for training with LoRA.
    
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
    Load and preprocess the distillation dataset for LoRA training.
    
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

def create_lora_config(r: int = 8, 
                      lora_alpha: int = 32, 
                      lora_dropout: float = 0.1,
                      target_modules: List[str] = None) -> LoraConfig:
    """
    Create LoRA configuration for GPT-2 model.
    
    Args:
        r: LoRA attention dimension
        lora_alpha: Alpha parameter for LoRA scaling
        lora_dropout: Dropout probability for LoRA layers
        target_modules: List of modules to apply LoRA to
        
    Returns:
        LoRA configuration
    """
    if target_modules is None:
        # Default target modules for GPT-2
        target_modules = [
            "c_attn",  # Attention layers
            "c_proj",  # Projection layers
        ]
    
    lora_config = LoraConfig(
        r=r,
        lora_alpha=lora_alpha,
        target_modules=target_modules,
        lora_dropout=lora_dropout,
        bias="none",
        task_type=TaskType.CAUSAL_LM
    )
    
    return lora_config

def main():
    parser = argparse.ArgumentParser(description="LoRA Integration for Distillation")
    parser.add_argument("--dataset_path", type=str, required=True,
                        help="Path to the distillation dataset")
    parser.add_argument("--output_dir", type=str, default="./gpt2-lora-distilled",
                        help="Directory to save the LoRA-adapted model")
    parser.add_argument("--model_name", type=str, default="gpt2-large",
                        help="Name/path of the student model")
    parser.add_argument("--max_length", type=int, default=1024,
                        help="Maximum sequence length")
    parser.add_argument("--per_device_train_batch_size", type=int, default=4,
                        help="Training batch size per device")
    parser.add_argument("--gradient_accumulation_steps", type=int, default=4,
                        help="Gradient accumulation steps")
    parser.add_argument("--learning_rate", type=float, default=1e-4,
                        help="Learning rate for LoRA parameters")
    parser.add_argument("--num_train_epochs", type=int, default=3,
                        help="Number of training epochs")
    parser.add_argument("--warmup_steps", type=int, default=100,
                        help="Number of warmup steps")
    parser.add_argument("--save_steps", type=int, default=500,
                        help="Save checkpoint every N steps")
    parser.add_argument("--logging_steps", type=int, default=10,
                        help="Log metrics every N steps")
    parser.add_argument("--lora_r", type=int, default=8,
                        help="LoRA attention dimension")
    parser.add_argument("--lora_alpha", type=int, default=32,
                        help="LoRA alpha parameter")
    parser.add_argument("--lora_dropout", type=float, default=0.1,
                        help="LoRA dropout probability")
    parser.add_argument("--fp16", action="store_true",
                        help="Use mixed precision training")
    
    args = parser.parse_args()
    
    # Load tokenizer and base model
    tokenizer = GPT2Tokenizer.from_pretrained(args.model_name)
    tokenizer.pad_token = tokenizer.eos_token
    
    model = GPT2LMHeadModel.from_pretrained(args.model_name)
    
    # Apply LoRA adaptation
    lora_config = create_lora_config(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
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
        evaluation_strategy="no",  # No evaluation for now
        num_train_epochs=args.num_train_epochs,
        fp16=args.fp16,
        report_to="none",  # Disable wandb/tensorboard
        logging_dir=f"{args.output_dir}/logs",
        save_total_limit=2,  # Keep only last 2 checkpoints
        dataloader_pin_memory=False,  # Reduce memory usage
    )
    
    # Setup trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )
    
    # Start training
    print("Starting LoRA distillation training...")
    trainer.train()
    
    # Save final model
    trainer.save_model()
    tokenizer.save_pretrained(args.output_dir)
    print(f"LoRA-adapted model saved to {args.output_dir}")

if __name__ == "__main__":
    main()