"""
Script to evaluate and compare outputs from teacher (GPT-NeoX) and student (GPT-2) models.
"""

import argparse
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from datasets import load_dataset
import json

def generate_text(model, tokenizer, prompt, max_new_tokens=100, device="cuda" if torch.cuda.is_available() else "cpu"):
    """
    Generate text using the provided model and tokenizer.
    """
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512).to(device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id
        )
    
    generated_text = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    return generated_text.strip()

def load_test_prompts(dataset_path):
    """
    Load test prompts from a JSON file.
    """
    with open(dataset_path, 'r') as f:
        if dataset_path.endswith('.json'):
            data = json.load(f)
            if isinstance(data, list):
                return [item['prompt'] for item in data if 'prompt' in item]
        elif dataset_path.endswith('.jsonl'):
            prompts = []
            for line in f:
                item = json.loads(line.strip())
                if 'prompt' in item:
                    prompts.append(item['prompt'])
            return prompts
    return []

def main():
    parser = argparse.ArgumentParser(description="Evaluate and compare teacher and student models")
    parser.add_argument("--test_prompts", type=str, required=True,
                        help="Path to test prompts (JSON/JSONL)")
    parser.add_argument("--teacher_model", type=str, default="EleutherAI/gpt-neox-20b",
                        help="Teacher model name/path")
    parser.add_argument("--student_model", type=str, required=True,
                        help="Student model name/path")
    parser.add_argument("--max_new_tokens", type=int, default=100,
                        help="Maximum number of new tokens to generate")
    parser.add_argument("--output_file", type=str, default="model_comparison.json",
                        help="File to save comparison results")
    
    args = parser.parse_args()
    
    # Load test prompts
    prompts = load_test_prompts(args.test_prompts)
    print(f"Loaded {len(prompts)} test prompts")
    
    # Setup device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Load teacher model
    print("Loading teacher model...")
    teacher_tokenizer = AutoTokenizer.from_pretrained(args.teacher_model)
    teacher_tokenizer.pad_token = teacher_tokenizer.eos_token
    teacher_model = AutoModelForCausalLM.from_pretrained(
        args.teacher_model,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        low_cpu_mem_usage=True
    ).to(device)
    teacher_model.eval()
    
    # Load student model
    print("Loading student model...")
    student_tokenizer = AutoTokenizer.from_pretrained(args.student_model)
    student_tokenizer.pad_token = student_tokenizer.eos_token
    student_model = AutoModelForCausalLM.from_pretrained(args.student_model).to(device)
    student_model.eval()
    
    # Generate comparisons
    comparisons = []
    for i, prompt in enumerate(prompts):
        print(f"Processing prompt {i+1}/{len(prompts)}: {prompt[:50]}...")
        
        # Generate teacher response
        teacher_response = generate_text(
            teacher_model, teacher_tokenizer, prompt, 
            max_new_tokens=args.max_new_tokens, device=device
        )
        
        # Generate student response
        student_response = generate_text(
            student_model, student_tokenizer, prompt, 
            max_new_tokens=args.max_new_tokens, device=device
        )
        
        # Store comparison
        comparison = {
            "prompt": prompt,
            "teacher_response": teacher_response,
            "student_response": student_response
        }
        comparisons.append(comparison)
    
    # Save results
    with open(args.output_file, 'w') as f:
        json.dump(comparisons, f, indent=2)
    
    print(f"Saved {len(comparisons)} comparisons to {args.output_file}")
    
    # Print sample comparison
    if comparisons:
        sample = comparisons[0]
        print("\n" + "="*50)
        print("SAMPLE COMPARISON")
        print("="*50)
        print(f"Prompt: {sample['prompt']}")
        print("-" * 30)
        print(f"Teacher: {sample['teacher_response']}")
        print("-" * 30)
        print(f"Student: {sample['student_response']}")
        print("="*50)

if __name__ == "__main__":
    main()