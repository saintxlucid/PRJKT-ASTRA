"""
Progressive Distillation: NeoX → Mistral 7B → GPT-2

This script implements a progressive distillation pipeline that bridges the gap between
large and small models by using intermediate models to reduce capacity shock.
"""

import argparse
import json
import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from tqdm import tqdm
from typing import List, Dict, Any

def generate_with_model(model, tokenizer, prompts: List[str], 
                       max_new_tokens: int = 256, 
                       device: str = "cuda" if torch.cuda.is_available() else "cpu") -> List[str]:
    """
    Generate responses using the provided model.
    
    Args:
        model: The model to use for generation
        tokenizer: The tokenizer for the model
        prompts: List of prompts to generate responses for
        max_new_tokens: Maximum number of new tokens to generate
        device: Device to run inference on
        
    Returns:
        List of generated responses
    """
    responses = []
    
    for prompt in tqdm(prompts, desc="Generating responses"):
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
        
        response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        responses.append(response.strip())
    
    return responses

def progressive_distillation_dataset(prompts: List[str], 
                                   intermediate_model_name: str = "mistralai/Mistral-7B-v0.1",
                                   teacher_model_name: str = "EleutherAI/gpt-neox-20b",
                                   max_new_tokens: int = 256) -> List[Dict[str, str]]:
    """
    Create a progressive distillation dataset by generating responses from both
    the teacher model and intermediate model.
    
    Args:
        prompts: List of prompts to generate responses for
        intermediate_model_name: Name of the intermediate model (Mistral 7B)
        teacher_model_name: Name of the teacher model (GPT-NeoX 20B)
        max_new_tokens: Maximum number of new tokens to generate
        
    Returns:
        Dataset with prompts and responses from both models
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Load intermediate model (Mistral 7B)
    print("Loading intermediate model (Mistral 7B)...")
    intermediate_tokenizer = AutoTokenizer.from_pretrained(intermediate_model_name)
    intermediate_tokenizer.pad_token = intermediate_tokenizer.eos_token
    
    intermediate_model = AutoModelForCausalLM.from_pretrained(
        intermediate_model_name,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        low_cpu_mem_usage=True
    ).to(device)
    intermediate_model.eval()
    
    # Load teacher model (GPT-NeoX 20B)
    print("Loading teacher model (GPT-NeoX 20B)...")
    teacher_tokenizer = AutoTokenizer.from_pretrained(teacher_model_name)
    teacher_tokenizer.pad_token = teacher_tokenizer.eos_token
    
    teacher_model = AutoModelForCausalLM.from_pretrained(
        teacher_model_name,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        low_cpu_mem_usage=True
    ).to(device)
    teacher_model.eval()
    
    # Generate responses from intermediate model
    print("Generating responses from intermediate model...")
    intermediate_responses = generate_with_model(
        intermediate_model, intermediate_tokenizer, prompts, max_new_tokens, device
    )
    
    # Generate responses from teacher model
    print("Generating responses from teacher model...")
    teacher_responses = generate_with_model(
        teacher_model, teacher_tokenizer, prompts, max_new_tokens, device
    )
    
    # Create dataset
    dataset = []
    for prompt, intermediate_resp, teacher_resp in zip(prompts, intermediate_responses, teacher_responses):
        dataset.append({
            "prompt": prompt,
            "intermediate_output": intermediate_resp,
            "teacher_output": teacher_resp
        })
    
    return dataset

def save_progressive_dataset(dataset: List[Dict[str, str]], output_path: str):
    """
    Save the progressive distillation dataset.
    
    Args:
        dataset: The dataset to save
        output_path: Path to save the dataset
    """
    with open(output_path, 'w') as f:
        json.dump(dataset, f, indent=2)
    print(f"Saved progressive distillation dataset with {len(dataset)} samples to {output_path}")

def load_prompts_from_file(prompt_file: str) -> List[str]:
    """
    Load prompts from a JSON/JSONL file.
    
    Args:
        prompt_file: Path to the prompt file
        
    Returns:
        List of prompts
    """
    prompts = []
    
    if prompt_file.endswith('.json'):
        with open(prompt_file, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                # Check if it's a list of dictionaries or strings
                if all(isinstance(item, str) for item in data):
                    prompts = data
                else:
                    # Extract prompts from dictionaries
                    prompts = [item.get('prompt', item.get('instruction', item.get('question', ''))) 
                              for item in data if isinstance(item, dict)]
    elif prompt_file.endswith('.jsonl'):
        with open(prompt_file, 'r') as f:
            for line in f:
                item = json.loads(line.strip())
                if isinstance(item, str):
                    prompts.append(item)
                else:
                    prompts.append(item.get('prompt', item.get('instruction', item.get('question', ''))))
    
    # Filter out empty prompts
    prompts = [p for p in prompts if p]
    return prompts

def main():
    parser = argparse.ArgumentParser(description="Progressive Distillation: NeoX → Mistral 7B → GPT-2")
    parser.add_argument("--prompt_file", type=str, required=True,
                        help="Path to the prompt file (JSON/JSONL)")
    parser.add_argument("--output_dataset", type=str, required=True,
                        help="Path to save the progressive distillation dataset")
    parser.add_argument("--intermediate_model", type=str, default="mistralai/Mistral-7B-v0.1",
                        help="Name/path of the intermediate model")
    parser.add_argument("--teacher_model", type=str, default="EleutherAI/gpt-neox-20b",
                        help="Name/path of the teacher model")
    parser.add_argument("--max_new_tokens", type=int, default=256,
                        help="Maximum number of new tokens to generate")
    
    args = parser.parse_args()
    
    # Load prompts
    prompts = load_prompts_from_file(args.prompt_file)
    print(f"Loaded {len(prompts)} prompts from {args.prompt_file}")
    
    # Create progressive distillation dataset
    dataset = progressive_distillation_dataset(
        prompts,
        intermediate_model_name=args.intermediate_model,
        teacher_model_name=args.teacher_model,
        max_new_tokens=args.max_new_tokens
    )
    
    # Save dataset
    save_progressive_dataset(dataset, args.output_dataset)

if __name__ == "__main__":
    main()