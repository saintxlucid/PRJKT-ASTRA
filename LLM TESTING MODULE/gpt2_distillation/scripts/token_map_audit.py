"""
Tokenizer Mapping Audit Script

Audit token coverage between teacher and student tokenizers.
Maps teacher tokens to student tokens where possible.
"""

import argparse
import json
from typing import Dict, List, Any, Tuple
from transformers import AutoTokenizer
import torch

def load_teacher_logits(dataset_path: str) -> List[Dict[str, Any]]:
    """
    Load teacher logits from dataset file.
    
    Args:
        dataset_path: Path to teacher logits dataset
        
    Returns:
        List of dataset examples with logits
    """
    with open(dataset_path, 'r') as f:
        if dataset_path.endswith('.json'):
            return json.load(f)
        elif dataset_path.endswith('.jsonl'):
            dataset = []
            for line in f:
                dataset.append(json.loads(line.strip()))
            return dataset

def build_token_mapping(teacher_tokenizer, student_tokenizer) -> Dict[int, int]:
    """
    Build mapping from teacher tokens to student tokens where possible.
    
    Args:
        teacher_tokenizer: Teacher model tokenizer
        student_tokenizer: Student model tokenizer
        
    Returns:
        Dictionary mapping teacher token IDs to student token IDs
    """
    token_mapping = {}
    
    # Iterate through teacher vocabulary
    for token_id, token_text in teacher_tokenizer.decoder.items():
        try:
            # Try to encode with student tokenizer
            student_ids = student_tokenizer.encode(token_text, add_special_tokens=False)
            
            # If it's a single token, we can map directly
            if len(student_ids) == 1:
                token_mapping[token_id] = student_ids[0]
        except:
            # If encoding fails, skip this token
            continue
    
    return token_mapping

def calculate_coverage_stats(teacher_tokenizer, student_tokenizer, 
                           token_mapping: Dict[int, int]) -> Dict[str, Any]:
    """
    Calculate token coverage statistics.
    
    Args:
        teacher_tokenizer: Teacher model tokenizer
        student_tokenizer: Student model tokenizer
        token_mapping: Teacher to student token mapping
        
    Returns:
        Coverage statistics
    """
    teacher_vocab_size = len(teacher_tokenizer)
    student_vocab_size = len(student_tokenizer)
    
    # Count mappable tokens
    mappable_tokens = len(token_mapping)
    
    # Calculate coverage percentage
    coverage_percentage = (mappable_tokens / teacher_vocab_size) * 100 if teacher_vocab_size > 0 else 0
    
    # Find unmappable tokens
    unmappable_tokens = teacher_vocab_size - mappable_tokens
    
    stats = {
        "teacher_vocab_size": teacher_vocab_size,
        "student_vocab_size": student_vocab_size,
        "mappable_tokens": mappable_tokens,
        "unmappable_tokens": unmappable_tokens,
        "coverage_percentage": coverage_percentage,
        "mapping_ratio": f"{mappable_tokens}/{teacher_vocab_size}"
    }
    
    return stats

def analyze_logits_coverage(dataset: List[Dict[str, Any]], 
                          token_mapping: Dict[int, int]) -> Dict[str, Any]:
    """
    Analyze coverage of teacher logits in student vocabulary.
    
    Args:
        dataset: Dataset with teacher logits
        token_mapping: Teacher to student token mapping
        
    Returns:
        Logits coverage statistics
    """
    total_logits = 0
    covered_logits = 0
    
    for example in dataset:
        if "logits" in example:
            logits_data = example["logits"]
            
            # Process each token's logits
            for token_logits in logits_data:
                total_logits += 1
                
                # Check if teacher token is mappable
                # Assuming token_logits is a list where first element is token_id
                if isinstance(token_logits, list) and len(token_logits) > 0:
                    teacher_token_id = token_logits[0]  # Assuming first element is token_id
                    if teacher_token_id in token_mapping:
                        covered_logits += 1
    
    coverage_percentage = (covered_logits / total_logits) * 100 if total_logits > 0 else 0
    
    stats = {
        "total_logits": total_logits,
        "covered_logits": covered_logits,
        "uncovered_logits": total_logits - covered_logits,
        "logits_coverage_percentage": coverage_percentage
    }
    
    return stats

def save_mapping(token_mapping: Dict[int, int], output_path: str):
    """
    Save token mapping to file.
    
    Args:
        token_mapping: Teacher to student token mapping
        output_path: Path to save mapping
    """
    # Convert to JSON-serializable format
    serializable_mapping = {str(k): v for k, v in token_mapping.items()}
    
    with open(output_path, 'w') as f:
        json.dump(serializable_mapping, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Audit token coverage between teacher and student tokenizers")
    parser.add_argument("--teacher", type=str, required=True,
                        help="Path to teacher logits dataset or teacher model name")
    parser.add_argument("--student", type=str, required=True,
                        help="Student model name or path")
    parser.add_argument("--mapping_output", type=str,
                        help="Path to save token mapping")
    parser.add_argument("--stats_output", type=str,
                        help="Path to save coverage statistics")
    
    args = parser.parse_args()
    
    # Load teacher tokenizer
    print("Loading teacher tokenizer...")
    if args.teacher.endswith('.json') or args.teacher.endswith('.jsonl'):
        # If teacher is a dataset file, load it and use a default tokenizer
        teacher_dataset = load_teacher_logits(args.teacher)
        # For this example, we'll use GPT-NeoX tokenizer as default
        teacher_tokenizer = AutoTokenizer.from_pretrained("EleutherAI/gpt-neox-20b")
    else:
        # If teacher is a model name, load its tokenizer
        teacher_tokenizer = AutoTokenizer.from_pretrained(args.teacher)
        teacher_dataset = None
    
    # Load student tokenizer
    print("Loading student tokenizer...")
    student_tokenizer = AutoTokenizer.from_pretrained(args.student)
    
    # Build token mapping
    print("Building token mapping...")
    token_mapping = build_token_mapping(teacher_tokenizer, student_tokenizer)
    
    # Calculate coverage statistics
    print("Calculating coverage statistics...")
    coverage_stats = calculate_coverage_stats(teacher_tokenizer, student_tokenizer, token_mapping)
    
    # Analyze logits coverage if dataset is available
    logits_stats = {}
    if teacher_dataset:
        print("Analyzing logits coverage...")
        logits_stats = analyze_logits_coverage(teacher_dataset, token_mapping)
        coverage_stats.update(logits_stats)
    
    # Print statistics
    print("\n" + "="*50)
    print("TOKEN COVERAGE STATISTICS")
    print("="*50)
    print(f"Teacher vocabulary size: {coverage_stats['teacher_vocab_size']:,}")
    print(f"Student vocabulary size: {coverage_stats['student_vocab_size']:,}")
    print(f"Mappable tokens: {coverage_stats['mappable_tokens']:,}")
    print(f"Unmappable tokens: {coverage_stats['unmappable_tokens']:,}")
    print(f"Token coverage: {coverage_stats['coverage_percentage']:.2f}%")
    print(f"Mapping ratio: {coverage_stats['mapping_ratio']}")
    
    if "logits_coverage_percentage" in coverage_stats:
        print(f"Logits coverage: {coverage_stats['logits_coverage_percentage']:.2f}%")
        print(f"Covered logits: {coverage_stats['covered_logits']:,}")
        print(f"Uncovered logits: {coverage_stats['uncovered_logits']:,}")
    
    print("="*50)
    
    # Save mapping if requested
    if args.mapping_output:
        save_mapping(token_mapping, args.mapping_output)
        print(f"Token mapping saved to {args.mapping_output}")
    
    # Save statistics if requested
    if args.stats_output:
        with open(args.stats_output, 'w') as f:
            json.dump(coverage_stats, f, indent=2)
        print(f"Coverage statistics saved to {args.stats_output}")

if __name__ == "__main__":
    main()