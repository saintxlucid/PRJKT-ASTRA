"""
Pairwise Comparison Script

Compare teacher and student model outputs side-by-side with win-rate calculation.
"""

import argparse
import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import List, Dict, Any, Tuple
import numpy as np

def generate_text(model, tokenizer, prompt: str, max_new_tokens: int = 100) -> str:
    """
    Generate text using the provided model and tokenizer.
    
    Args:
        model: Model to use for generation
        tokenizer: Tokenizer for the model
        prompt: Input prompt
        max_new_tokens: Maximum number of new tokens to generate
        
    Returns:
        Generated text
    """
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
    
    # Move to GPU if available
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}
        model = model.cuda()
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id
        )
    
    generated_text = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return generated_text.strip()

def load_test_prompts(prompt_file: str) -> List[str]:
    """
    Load test prompts from file.
    
    Args:
        prompt_file: Path to prompt file
        
    Returns:
        List of prompts
    """
    prompts = []
    
    with open(prompt_file, 'r') as f:
        if prompt_file.endswith('.json'):
            data = json.load(f)
            if isinstance(data, list):
                # Extract prompts from dictionaries or use strings directly
                for item in data:
                    if isinstance(item, str):
                        prompts.append(item)
                    elif isinstance(item, dict):
                        prompts.append(item.get('prompt', item.get('question', '')))
        elif prompt_file.endswith('.jsonl'):
            for line in f:
                item = json.loads(line.strip())
                if isinstance(item, str):
                    prompts.append(item)
                elif isinstance(item, dict):
                    prompts.append(item.get('prompt', item.get('question', '')))
    
    # Filter out empty prompts
    return [p for p in prompts if p]

def simple_judge(teacher_output: str, student_output: str, prompt: str) -> str:
    """
    Simple heuristic judge to compare outputs.
    
    Args:
        teacher_output: Teacher model output
        student_output: Student model output
        prompt: Input prompt
        
    Returns:
        Winner ('teacher', 'student', or 'tie')
    """
    # Simple heuristics for comparison
    # In practice, you would use a more sophisticated judge model
    
    # Length comparison (prefer more detailed responses, but not too long)
    teacher_len = len(teacher_output)
    student_len = len(student_output)
    
    # Relevance check (count prompt keywords in output)
    prompt_words = set(prompt.lower().split())
    teacher_relevance = sum(1 for word in prompt_words if word in teacher_output.lower())
    student_relevance = sum(1 for word in prompt_words if word in student_output.lower())
    
    # Quality heuristics
    if abs(teacher_len - student_len) > 200:
        # If one is much longer, prefer the more moderate length
        if 50 < min(teacher_len, student_len) < 300:
            winner = 'teacher' if teacher_len < student_len else 'student'
        else:
            winner = 'teacher' if teacher_len > student_len else 'student'
    elif abs(teacher_relevance - student_relevance) > 2:
        # Prefer higher relevance
        winner = 'teacher' if teacher_relevance > student_relevance else 'student'
    else:
        # Tie or need more sophisticated judging
        winner = 'tie'
    
    return winner

def run_pairwise_comparison(teacher_model_name: str, 
                          student_model_name: str, 
                          prompts: List[str],
                          max_new_tokens: int = 100) -> Dict[str, Any]:
    """
    Run pairwise comparison between teacher and student models.
    
    Args:
        teacher_model_name: Name/path of teacher model
        student_model_name: Name/path of student model
        prompts: List of prompts to compare on
        max_new_tokens: Maximum tokens to generate
        
    Returns:
        Comparison results
    """
    # Load models and tokenizers
    print("Loading teacher model...")
    teacher_tokenizer = AutoTokenizer.from_pretrained(teacher_model_name)
    teacher_tokenizer.pad_token = teacher_tokenizer.eos_token
    teacher_model = AutoModelForCausalLM.from_pretrained(teacher_model_name)
    
    print("Loading student model...")
    student_tokenizer = AutoTokenizer.from_pretrained(student_model_name)
    student_tokenizer.pad_token = student_tokenizer.eos_token
    student_model = AutoModelForCausalLM.from_pretrained(student_model_name)
    
    # Run comparisons
    results = {
        "teacher_wins": 0,
        "student_wins": 0,
        "ties": 0,
        "comparisons": []
    }
    
    for i, prompt in enumerate(prompts):
        print(f"Processing prompt {i+1}/{len(prompts)}: {prompt[:50]}...")
        
        # Generate outputs
        teacher_output = generate_text(teacher_model, teacher_tokenizer, prompt, max_new_tokens)
        student_output = generate_text(student_model, student_tokenizer, prompt, max_new_tokens)
        
        # Judge outputs
        winner = simple_judge(teacher_output, student_output, prompt)
        
        # Update results
        if winner == 'teacher':
            results["teacher_wins"] += 1
        elif winner == 'student':
            results["student_wins"] += 1
        else:
            results["ties"] += 1
            
        # Store comparison
        comparison = {
            "prompt": prompt,
            "teacher_output": teacher_output,
            "student_output": student_output,
            "winner": winner
        }
        results["comparisons"].append(comparison)
    
    # Calculate win rates
    total_comparisons = len(prompts)
    results["teacher_win_rate"] = results["teacher_wins"] / total_comparisons
    results["student_win_rate"] = results["student_wins"] / total_comparisons
    results["tie_rate"] = results["ties"] / total_comparisons
    
    return results

def save_results(results: Dict[str, Any], output_file: str):
    """
    Save results to JSON file.
    
    Args:
        results: Comparison results
        output_file: Path to output file
    """
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Pairwise comparison of teacher and student models")
    parser.add_argument("--teacher", type=str, required=True,
                        help="Teacher model name or path")
    parser.add_argument("--student", type=str, required=True,
                        help="Student model name or path")
    parser.add_argument("--prompts", type=str, required=True,
                        help="Path to test prompts file")
    parser.add_argument("--max_new_tokens", type=int, default=100,
                        help="Maximum number of new tokens to generate")
    parser.add_argument("--output", type=str, default="pairwise_comparison_results.json",
                        help="Path to save results")
    
    args = parser.parse_args()
    
    # Load prompts
    prompts = load_test_prompts(args.prompts)
    print(f"Loaded {len(prompts)} test prompts")
    
    # Run pairwise comparison
    print("Running pairwise comparison...")
    results = run_pairwise_comparison(
        args.teacher,
        args.student,
        prompts,
        args.max_new_tokens
    )
    
    # Print summary
    print("\n" + "="*50)
    print("PAIRWISE COMPARISON RESULTS")
    print("="*50)
    print(f"Teacher win rate: {results['teacher_win_rate']:.2%}")
    print(f"Student win rate: {results['student_win_rate']:.2%}")
    print(f"Tie rate: {results['tie_rate']:.2%}")
    print(f"Total comparisons: {len(results['comparisons'])}")
    print("="*50)
    
    # Save results
    save_results(results, args.output)
    print(f"Results saved to {args.output}")

if __name__ == "__main__":
    main()