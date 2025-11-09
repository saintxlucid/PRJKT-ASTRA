"""
Utility functions for managing and processing distillation datasets.
"""

import json
import random
from typing import List, Dict, Any
from datasets import Dataset, load_dataset

def load_json_dataset(file_path: str) -> List[Dict[str, Any]]:
    """
    Load a dataset from a JSON or JSONL file.
    
    Args:
        file_path: Path to the JSON/JSONL file
        
    Returns:
        List of dataset entries
    """
    data = []
    
    if file_path.endswith('.json'):
        with open(file_path, 'r') as f:
            data = json.load(f)
    elif file_path.endswith('.jsonl'):
        with open(file_path, 'r') as f:
            for line in f:
                data.append(json.loads(line.strip()))
                
    return data

def save_json_dataset(data: List[Dict[str, Any]], file_path: str) -> None:
    """
    Save dataset to a JSON file.
    
    Args:
        data: List of dataset entries
        file_path: Path to save the JSON file
    """
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def merge_datasets(dataset_paths: List[str]) -> List[Dict[str, Any]]:
    """
    Merge multiple datasets into one.
    
    Args:
        dataset_paths: List of paths to dataset files
        
    Returns:
        Merged dataset
    """
    merged_data = []
    
    for path in dataset_paths:
        data = load_json_dataset(path)
        merged_data.extend(data)
        
    return merged_data

def sample_dataset(dataset: List[Dict[str, Any]], sample_size: int) -> List[Dict[str, Any]]:
    """
    Randomly sample a subset of the dataset.
    
    Args:
        dataset: Full dataset
        sample_size: Number of samples to select
        
    Returns:
        Sampled dataset
    """
    if len(dataset) <= sample_size:
        return dataset[:]
    
    return random.sample(dataset, sample_size)

def filter_dataset(dataset: List[Dict[str, Any]], 
                  min_prompt_length: int = 10,
                  min_response_length: int = 20,
                  max_prompt_length: int = 1000,
                  max_response_length: int = 2000) -> List[Dict[str, Any]]:
    """
    Filter dataset based on text length criteria.
    
    Args:
        dataset: Input dataset
        min_prompt_length: Minimum prompt length
        min_response_length: Minimum response length
        max_prompt_length: Maximum prompt length
        max_response_length: Maximum response length
        
    Returns:
        Filtered dataset
    """
    filtered = []
    
    for item in dataset:
        prompt = item.get('prompt', '')
        response = item.get('neox_output', item.get('response', ''))
        
        if (min_prompt_length <= len(prompt) <= max_prompt_length and
            min_response_length <= len(response) <= max_response_length):
            filtered.append(item)
            
    return filtered

def split_dataset(dataset: List[Dict[str, Any]], 
                 train_ratio: float = 0.8,
                 val_ratio: float = 0.1,
                 test_ratio: float = 0.1) -> Dict[str, List[Dict[str, Any]]]:
    """
    Split dataset into train/validation/test sets.
    
    Args:
        dataset: Input dataset
        train_ratio: Proportion for training set
        val_ratio: Proportion for validation set
        test_ratio: Proportion for test set
        
    Returns:
        Dictionary with train/val/test splits
    """
    # Normalize ratios
    total = train_ratio + val_ratio + test_ratio
    train_ratio /= total
    val_ratio /= total
    test_ratio /= total
    
    # Shuffle dataset
    shuffled = dataset[:]
    random.shuffle(shuffled)
    
    # Calculate split indices
    n = len(shuffled)
    train_end = int(n * train_ratio)
    val_end = train_end + int(n * val_ratio)
    
    # Split dataset
    splits = {
        'train': shuffled[:train_end],
        'validation': shuffled[train_end:val_end],
        'test': shuffled[val_end:]
    }
    
    return splits

def analyze_dataset(dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze dataset statistics.
    
    Args:
        dataset: Input dataset
        
    Returns:
        Dictionary with dataset statistics
    """
    if not dataset:
        return {}
        
    prompts = [item.get('prompt', '') for item in dataset]
    responses = [item.get('neox_output', item.get('response', '')) for item in dataset]
    
    prompt_lengths = [len(p) for p in prompts]
    response_lengths = [len(r) for r in responses]
    
    stats = {
        'total_samples': len(dataset),
        'prompt_length': {
            'min': min(prompt_lengths),
            'max': max(prompt_lengths),
            'avg': sum(prompt_lengths) / len(prompt_lengths)
        },
        'response_length': {
            'min': min(response_lengths),
            'max': max(response_lengths),
            'avg': sum(response_lengths) / len(response_lengths)
        },
        'sample_prompt': prompts[0] if prompts else '',
        'sample_response': responses[0] if responses else ''
    }
    
    return stats

def convert_huggingface_dataset(dataset_name: str, 
                              split: str = "train",
                              prompt_field: str = "prompt",
                              response_field: str = "response") -> List[Dict[str, Any]]:
    """
    Convert a Hugging Face dataset to our format.
    
    Args:
        dataset_name: Name of the Hugging Face dataset
        split: Dataset split to use
        prompt_field: Field name for prompts
        response_field: Field name for responses
        
    Returns:
        Converted dataset
    """
    # Load dataset
    hf_dataset = load_dataset(dataset_name, split=split)
    
    # Convert to our format
    converted = []
    for item in hf_dataset:
        if prompt_field in item and response_field in item:
            converted.append({
                'prompt': item[prompt_field],
                'neox_output': item[response_field]
            })
    
    return converted

def main():
    """Example usage of dataset utilities."""
    # Example: Analyze a dataset
    print("Dataset Utilities Example")
    print("=" * 30)
    
    # Create a sample dataset for demonstration
    sample_data = [
        {"prompt": "What is 2+2?", "neox_output": "2+2 equals 4."},
        {"prompt": "Explain photosynthesis", "neox_output": "Photosynthesis is the process by which plants convert light energy into chemical energy."},
        {"prompt": "Short prompt", "neox_output": "Short response"}
    ]
    
    # Analyze dataset
    stats = analyze_dataset(sample_data)
    print("Sample Dataset Statistics:")
    print(f"Total samples: {stats['total_samples']}")
    print(f"Average prompt length: {stats['prompt_length']['avg']:.1f}")
    print(f"Average response length: {stats['response_length']['avg']:.1f}")
    
    # Filter dataset
    filtered = filter_dataset(sample_data, min_prompt_length=10, min_response_length=15)
    print(f"\nFiltered dataset size: {len(filtered)}")
    
    # Split dataset
    splits = split_dataset(sample_data, train_ratio=0.6, val_ratio=0.2, test_ratio=0.2)
    print(f"Train set size: {len(splits['train'])}")
    print(f"Validation set size: {len(splits['validation'])}")
    print(f"Test set size: {len(splits['test'])}")

if __name__ == "__main__":
    main()