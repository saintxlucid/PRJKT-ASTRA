"""
Experiment: Compare Different Distillation Methods

This script runs experiments comparing different distillation methods and tracks their performance.
"""

import argparse
import json
import os
import torch
from transformers import GPT2Tokenizer, GPT2LMHeadModel
from datasets import load_dataset
import pandas as pd
from typing import Dict, List, Any

def calculate_perplexity(model, tokenizer, texts: List[str], 
                        device: str = "cuda" if torch.cuda.is_available() else "cpu",
                        max_length: int = 1024) -> float:
    """
    Calculate perplexity of a model on given texts.
    
    Args:
        model: The model to evaluate
        tokenizer: The tokenizer for the model
        texts: List of texts to evaluate on
        device: Device to run evaluation on
        max_length: Maximum sequence length
        
    Returns:
        Perplexity score
    """
    model.eval()
    total_loss = 0
    total_tokens = 0
    
    with torch.no_grad():
        for text in texts:
            # Tokenize input
            inputs = tokenizer(
                text, 
                return_tensors="pt", 
                truncation=True, 
                max_length=max_length,
                padding=True
            ).to(device)
            
            # Forward pass
            outputs = model(**inputs, labels=inputs["input_ids"])
            loss = outputs.loss
            
            # Count tokens
            tokens_in_batch = inputs["attention_mask"].sum().item()
            
            # Accumulate
            total_loss += loss.item() * tokens_in_batch
            total_tokens += tokens_in_batch
    
    # Calculate perplexity
    avg_loss = total_loss / total_tokens
    perplexity = torch.exp(torch.tensor(avg_loss)).item()
    
    return perplexity

def load_test_texts(dataset_path: str, sample_size: int = 100) -> List[str]:
    """
    Load test texts from dataset.
    
    Args:
        dataset_path: Path to the dataset
        sample_size: Number of samples to use for evaluation
        
    Returns:
        List of test texts
    """
    with open(dataset_path, 'r') as f:
        if dataset_path.endswith('.json'):
            data = json.load(f)
        elif dataset_path.endswith('.jsonl'):
            data = []
            for line in f:
                data.append(json.loads(line.strip()))
    
    # Extract texts
    texts = []
    for item in data:
        if 'prompt' in item and 'neox_output' in item:
            full_text = f"### PROMPT:\n{item['prompt']}\n\n### RESPONSE:\n{item['neox_output']}"
            texts.append(full_text)
        elif 'text' in item:
            texts.append(item['text'])
    
    # Sample if needed
    if len(texts) > sample_size:
        import random
        texts = random.sample(texts, sample_size)
    
    return texts

def compare_models(model_paths: List[str], 
                  model_names: List[str],
                  test_dataset: str,
                  max_length: int = 1024) -> Dict[str, float]:
    """
    Compare multiple models on test dataset.
    
    Args:
        model_paths: List of paths to model directories
        model_names: List of model names for reporting
        test_dataset: Path to test dataset
        max_length: Maximum sequence length
        
    Returns:
        Dictionary mapping model names to perplexity scores
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Load test texts
    print("Loading test texts...")
    test_texts = load_test_texts(test_dataset)
    print(f"Loaded {len(test_texts)} test samples")
    
    # Load tokenizer (assuming same tokenizer for all models)
    print("Loading tokenizer...")
    tokenizer = GPT2Tokenizer.from_pretrained(model_paths[0])
    tokenizer.pad_token = tokenizer.eos_token
    
    # Compare models
    results = {}
    for model_path, model_name in zip(model_paths, model_names):
        print(f"\nEvaluating {model_name}...")
        
        # Load model
        model = GPT2LMHeadModel.from_pretrained(model_path).to(device)
        
        # Calculate perplexity
        perplexity = calculate_perplexity(model, tokenizer, test_texts, device, max_length)
        results[model_name] = perplexity
        
        print(f"{model_name} perplexity: {perplexity:.2f}")
    
    return results

def save_results(results: Dict[str, float], output_file: str):
    """
    Save results to CSV file.
    
    Args:
        results: Dictionary of results
        output_file: Path to output file
    """
    # Convert to DataFrame
    df = pd.DataFrame(list(results.items()), columns=['Model', 'Perplexity'])
    df = df.sort_values('Perplexity')
    
    # Save to CSV
    df.to_csv(output_file, index=False)
    print(f"Results saved to {output_file}")
    
    # Print results
    print("\n" + "="*50)
    print("MODEL COMPARISON RESULTS")
    print("="*50)
    for model_name, perplexity in df.values:
        print(f"{model_name:30} {perplexity:.2f}")

def main():
    parser = argparse.ArgumentParser(description="Compare Distillation Methods")
    parser.add_argument("--models", type=str, nargs='+', required=True,
                        help="Paths to model directories")
    parser.add_argument("--names", type=str, nargs='+', required=True,
                        help="Names of models for reporting")
    parser.add_argument("--test_dataset", type=str, required=True,
                        help="Path to test dataset")
    parser.add_argument("--output_file", type=str, default="experiment_results.csv",
                        help="Path to save results")
    parser.add_argument("--max_length", type=int, default=1024,
                        help="Maximum sequence length")
    
    args = parser.parse_args()
    
    # Validate inputs
    if len(args.models) != len(args.names):
        raise ValueError("Number of model paths must match number of model names")
    
    # Compare models
    results = compare_models(args.models, args.names, args.test_dataset, args.max_length)
    
    # Save results
    save_results(results, args.output_file)

if __name__ == "__main__":
    main()