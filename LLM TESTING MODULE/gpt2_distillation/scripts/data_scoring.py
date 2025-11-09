"""
Data Scoring Script

Implements active & uncertainty sampling using teacher's token-level entropy.
Scores each example and applies entropy-based weighting.
"""

import argparse
import json
import torch
import numpy as np
from typing import List, Dict, Any
from tqdm import tqdm

def calculate_token_entropy(logits: torch.Tensor) -> float:
    """
    Calculate token-level entropy from logits.
    
    Args:
        logits: Logits tensor of shape [seq_len, vocab_size]
        
    Returns:
        Entropy value
    """
    # Convert logits to probabilities
    probs = torch.softmax(logits, dim=-1)
    
    # Calculate entropy: -sum(p * log(p))
    log_probs = torch.log(probs + 1e-8)  # Add small epsilon to avoid log(0)
    entropy = -torch.sum(probs * log_probs, dim=-1)
    
    # Return mean entropy across sequence
    return torch.mean(entropy).item()

def score_examples_with_entropy(dataset: List[Dict[str, Any]], 
                               logits_key: str = "logits") -> List[Dict[str, Any]]:
    """
    Score examples in dataset using token-level entropy.
    
    Args:
        dataset: List of dataset examples
        logits_key: Key for logits in each example
        
    Returns:
        Dataset with entropy scores added
    """
    scored_dataset = []
    
    for example in tqdm(dataset, desc="Scoring examples"):
        # Get logits
        if logits_key in example and example[logits_key]:
            logits = torch.tensor(example[logits_key])
            entropy = calculate_token_entropy(logits)
        else:
            # If no logits, use a default entropy value
            entropy = 0.0
        
        # Add entropy score to example
        scored_example = example.copy()
        scored_example["entropy"] = entropy
        scored_dataset.append(scored_example)
    
    return scored_dataset

def apply_entropy_weighting(dataset: List[Dict[str, Any]], 
                          a: float = 0.5, 
                          b: float = 0.8, 
                          w_min: float = 0.3, 
                          w_max: float = 1.5) -> List[Dict[str, Any]]:
    """
    Apply entropy-based weighting to examples.
    
    Weight formula: w = clip(a + b * H_teacher, w_min, w_max)
    
    Args:
        dataset: Dataset with entropy scores
        a: Offset parameter
        b: Scaling parameter
        w_min: Minimum weight
        w_max: Maximum weight
        
    Returns:
        Dataset with weights added
    """
    weighted_dataset = []
    
    for example in dataset:
        if "entropy" in example:
            # Calculate weight
            weight = a + b * example["entropy"]
            weight = max(w_min, min(w_max, weight))  # Clip to range
        else:
            # Default weight
            weight = 1.0
            
        # Add weight to example
        weighted_example = example.copy()
        weighted_example["weight"] = weight
        weighted_dataset.append(weighted_example)
    
    return weighted_dataset

def create_hard_set(dataset: List[Dict[str, Any]], 
                   percentile: float = 95) -> List[Dict[str, Any]]:
    """
    Create a "hard set" from high-entropy examples.
    
    Args:
        dataset: Dataset with entropy scores
        percentile: Percentile threshold for hard examples
        
    Returns:
        Hard set of examples
    """
    # Get entropy values
    entropies = [example["entropy"] for example in dataset if "entropy" in example]
    
    if not entropies:
        return []
    
    # Calculate threshold
    threshold = np.percentile(entropies, percentile)
    
    # Filter hard examples
    hard_set = [example for example in dataset 
                if "entropy" in example and example["entropy"] >= threshold]
    
    return hard_set

def load_dataset(dataset_path: str) -> List[Dict[str, Any]]:
    """
    Load dataset from JSON/JSONL file.
    
    Args:
        dataset_path: Path to dataset file
        
    Returns:
        Loaded dataset
    """
    with open(dataset_path, 'r') as f:
        if dataset_path.endswith('.json'):
            return json.load(f)
        elif dataset_path.endswith('.jsonl'):
            dataset = []
            for line in f:
                dataset.append(json.loads(line.strip()))
            return dataset

def save_dataset(dataset: List[Dict[str, Any]], output_path: str):
    """
    Save dataset to JSON/JSONL file.
    
    Args:
        dataset: Dataset to save
        output_path: Path to save dataset
    """
    with open(output_path, 'w') as f:
        if output_path.endswith('.json'):
            json.dump(dataset, f, indent=2)
        elif output_path.endswith('.jsonl'):
            for example in dataset:
                f.write(json.dumps(example) + '\n')

def main():
    parser = argparse.ArgumentParser(description="Score dataset examples using entropy")
    parser.add_argument("--input_dataset", type=str, required=True,
                        help="Path to input dataset")
    parser.add_argument("--output_dataset", type=str, required=True,
                        help="Path to output scored dataset")
    parser.add_argument("--hard_set", type=str,
                        help="Path to save hard set (optional)")
    parser.add_argument("--hard_percentile", type=float, default=95,
                        help="Percentile for hard set threshold")
    parser.add_argument("--weighting_a", type=float, default=0.5,
                        help="Entropy weighting offset parameter")
    parser.add_argument("--weighting_b", type=float, default=0.8,
                        help="Entropy weighting scaling parameter")
    parser.add_argument("--weighting_min", type=float, default=0.3,
                        help="Minimum weight")
    parser.add_argument("--weighting_max", type=float, default=1.5,
                        help="Maximum weight")
    parser.add_argument("--logits_key", type=str, default="logits",
                        help="Key for logits in dataset examples")
    
    args = parser.parse_args()
    
    # Load dataset
    print("Loading dataset...")
    dataset = load_dataset(args.input_dataset)
    print(f"Loaded {len(dataset)} examples")
    
    # Score examples with entropy
    print("Scoring examples with entropy...")
    scored_dataset = score_examples_with_entropy(dataset, args.logits_key)
    
    # Apply entropy weighting
    print("Applying entropy weighting...")
    weighted_dataset = apply_entropy_weighting(
        scored_dataset,
        args.weighting_a,
        args.weighting_b,
        args.weighting_min,
        args.weighting_max
    )
    
    # Save scored dataset
    print("Saving scored dataset...")
    save_dataset(weighted_dataset, args.output_dataset)
    print(f"Saved {len(weighted_dataset)} scored examples to {args.output_dataset}")
    
    # Create hard set if requested
    if args.hard_set:
        print("Creating hard set...")
        hard_set = create_hard_set(weighted_dataset, args.hard_percentile)
        save_dataset(hard_set, args.hard_set)
        print(f"Saved {len(hard_set)} hard examples to {args.hard_set}")

if __name__ == "__main__":
    main()