"""
Chain-of-Thought (CoT) Distillation

This script implements CoT distillation by generating reasoning steps from GPT-NeoX 20B
and training GPT-2 to mimic the reasoning process.
"""

import argparse
import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from tqdm import tqdm
from typing import List, Dict, Any

def generate_cot_responses(prompts: List[str], 
                          model_name: str = "EleutherAI/gpt-neox-20b",
                          max_new_tokens: int = 512,
                          cot_trigger: str = "Let's think step by step.") -> List[Dict[str, str]]:
    """
    Generate CoT responses from the teacher model.
    
    Args:
        prompts: List of prompts to generate CoT responses for
        model_name: Name of the teacher model
        max_new_tokens: Maximum number of new tokens to generate
        cot_trigger: Trigger phrase to encourage step-by-step reasoning
        
    Returns:
        List of prompt-CoT response pairs
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        low_cpu_mem_usage=True
    ).to(device)
    model.eval()
    
    cot_dataset = []
    
    for prompt in tqdm(prompts, desc="Generating CoT responses"):
        # Format prompt with CoT trigger
        cot_prompt = f"{prompt}\n\n{cot_trigger}"
        
        # Tokenize input
        inputs = tokenizer(cot_prompt, return_tensors="pt", truncation=True, max_length=512).to(device)
        
        # Generate response
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # Decode response
        response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        
        # Combine prompt and response
        full_response = f"{cot_trigger} {response.strip()}"
        
        cot_dataset.append({
            "prompt": prompt,
            "cot_output": full_response
        })
    
    return cot_dataset

def save_cot_dataset(dataset: List[Dict[str, str]], output_path: str):
    """
    Save the CoT distillation dataset.
    
    Args:
        dataset: The CoT dataset to save
        output_path: Path to save the dataset
    """
    with open(output_path, 'w') as f:
        json.dump(dataset, f, indent=2)
    print(f"Saved CoT dataset with {len(dataset)} samples to {output_path}")

def load_prompts(prompt_file: str) -> List[str]:
    """
    Load prompts from a JSON/JSONL file.
    
    Args:
        prompt_file: Path to the prompt file
        
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

def create_cot_training_examples(cot_dataset: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Create training examples formatted for CoT distillation.
    
    Args:
        cot_dataset: Dataset with prompt-CoT output pairs
        
    Returns:
        Formatted training examples
    """
    training_examples = []
    
    for item in cot_dataset:
        # Format as instruction following
        full_text = f"### Problem:\n{item['prompt']}\n\n### Solution:\n{item['cot_output']}"
        
        training_examples.append({
            "prompt": item["prompt"],
            "cot_output": item["cot_output"],
            "full_text": full_text
        })
    
    return training_examples

def main():
    parser = argparse.ArgumentParser(description="Chain-of-Thought Distillation")
    parser.add_argument("--prompt_file", type=str, required=True,
                        help="Path to the prompt file (JSON/JSONL)")
    parser.add_argument("--output_dataset", type=str, required=True,
                        help="Path to save the CoT distillation dataset")
    parser.add_argument("--model_name", type=str, default="EleutherAI/gpt-neox-20b",
                        help="Name/path of the teacher model")
    parser.add_argument("--max_new_tokens", type=int, default=512,
                        help="Maximum number of new tokens to generate")
    parser.add_argument("--cot_trigger", type=str, default="Let's think step by step.",
                        help="Trigger phrase to encourage step-by-step reasoning")
    
    args = parser.parse_args()
    
    # Load prompts
    prompts = load_prompts(args.prompt_file)
    print(f"Loaded {len(prompts)} prompts from {args.prompt_file}")
    
    # Generate CoT responses
    print("Generating CoT responses...")
    cot_dataset = generate_cot_responses(
        prompts,
        model_name=args.model_name,
        max_new_tokens=args.max_new_tokens,
        cot_trigger=args.cot_trigger
    )
    
    # Create training examples
    training_examples = create_cot_training_examples(cot_dataset)
    
    # Save dataset
    save_cot_dataset(training_examples, args.output_dataset)
    print("CoT distillation dataset creation completed!")

if __name__ == "__main__":
    main()