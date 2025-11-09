"""
Script to calculate perplexity of trained models on a test dataset.
"""

import argparse
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForCausalLM
from torch.utils.data import DataLoader
from datasets import Dataset
import json

def prepare_test_dataset(test_file, tokenizer, max_length=1024):
    """
    Prepare test dataset for perplexity calculation.
    """
    # Load test data
    with open(test_file, 'r') as f:
        if test_file.endswith('.json'):
            data = json.load(f)
        elif test_file.endswith('.jsonl'):
            data = []
            for line in f:
                data.append(json.loads(line.strip()))
    
    # Extract texts (assuming they have 'prompt' and 'neox_output' keys)
    texts = []
    for item in data:
        if 'prompt' in item and 'neox_output' in item:
            full_text = f"### PROMPT:\n{item['prompt']}\n\n### RESPONSE:\n{item['neox_output']}"
            texts.append(full_text)
        elif 'text' in item:
            texts.append(item['text'])
    
    # Tokenize texts
    encodings = tokenizer(
        texts,
        truncation=True,
        padding=True,
        max_length=max_length,
        return_tensors="pt"
    )
    
    # Create dataset
    dataset = Dataset.from_dict({
        "input_ids": encodings["input_ids"],
        "attention_mask": encodings["attention_mask"]
    })
    
    return dataset

def calculate_perplexity(model, dataset, tokenizer, device, batch_size=2):
    """
    Calculate perplexity of the model on the given dataset.
    """
    model.eval()
    
    # Create data loader
    dataloader = DataLoader(dataset, batch_size=batch_size)
    
    total_loss = 0
    total_tokens = 0
    
    with torch.no_grad():
        for batch in dataloader:
            # Move batch to device
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            
            # Forward pass
            outputs = model(input_ids, attention_mask=attention_mask, labels=input_ids)
            loss = outputs.loss
            
            # Calculate number of tokens (excluding padding)
            tokens_in_batch = attention_mask.sum().item()
            
            # Accumulate loss and tokens
            total_loss += loss.item() * tokens_in_batch
            total_tokens += tokens_in_batch
    
    # Calculate perplexity
    avg_loss = total_loss / total_tokens
    perplexity = np.exp(avg_loss)
    
    return perplexity

def main():
    parser = argparse.ArgumentParser(description="Calculate model perplexity")
    parser.add_argument("--test_dataset", type=str, required=True,
                        help="Path to test dataset (JSON/JSONL)")
    parser.add_argument("--model_path", type=str, required=True,
                        help="Path to the model directory")
    parser.add_argument("--model_type", type=str, choices=["gpt2", "neox"], default="gpt2",
                        help="Type of model (affects tokenizer)")
    parser.add_argument("--max_length", type=int, default=1024,
                        help="Maximum sequence length")
    parser.add_argument("--batch_size", type=int, default=2,
                        help="Batch size for evaluation")
    
    args = parser.parse_args()
    
    # Setup device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Load tokenizer and model
    print("Loading model and tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_path)
    tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(args.model_path).to(device)
    
    # Prepare dataset
    print("Preparing test dataset...")
    dataset = prepare_test_dataset(args.test_dataset, tokenizer, args.max_length)
    print(f"Dataset contains {len(dataset)} samples")
    
    # Calculate perplexity
    print("Calculating perplexity...")
    perplexity = calculate_perplexity(model, dataset, tokenizer, device, args.batch_size)
    
    print(f"Model perplexity: {perplexity:.2f}")
    
    # Save result
    result = {
        "model_path": args.model_path,
        "perplexity": perplexity,
        "test_dataset": args.test_dataset
    }
    
    result_file = f"{args.model_path}/perplexity_result.json"
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"Results saved to {result_file}")

if __name__ == "__main__":
    main()