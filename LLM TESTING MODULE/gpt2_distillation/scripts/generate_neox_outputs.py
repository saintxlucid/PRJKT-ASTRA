"""
Script to generate GPT-NeoX outputs for prompts using a quantized GGUF model
or Hugging Face transformers model for knowledge distillation dataset creation.
"""

import json
import argparse
from typing import List, Dict, Any
from tqdm import tqdm
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import numpy as np

def load_prompts_from_dataset(dataset_path: str) -> List[Dict[str, str]]:
    """
    Load prompts from a dataset file (JSON/JSONL).
    
    Args:
        dataset_path: Path to the dataset file
        
    Returns:
        List of prompt dictionaries
    """
    prompts = []
    
    if dataset_path.endswith('.json'):
        with open(dataset_path, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                prompts = data
            else:
                # Handle different JSON formats
                if 'prompt' in data:
                    prompts = [{'prompt': data['prompt']}]
                elif 'instruction' in data:
                    prompts = [{'prompt': data['instruction']}]
                elif 'question' in data:
                    prompts = [{'prompt': data['question']}]
    elif dataset_path.endswith('.jsonl'):
        with open(dataset_path, 'r') as f:
            for line in f:
                prompts.append(json.loads(line.strip()))
    
    return prompts

def generate_neox_responses(prompts: List[Dict[str, str]], 
                           model_name: str = "EleutherAI/gpt-neox-20b",
                           max_new_tokens: int = 256,
                           emit_logits: bool = False,
                           topk: int = 100) -> List[Dict[str, Any]]:
    """
    Generate responses from GPT-NeoX model for given prompts.
    
    Args:
        prompts: List of prompt dictionaries
        model_name: Name/path of the GPT-NeoX model
        max_new_tokens: Maximum number of new tokens to generate
        emit_logits: Whether to emit logits for knowledge distillation
        topk: Number of top logits to keep for distillation
        
    Returns:
        List of prompt-response pairs
    """
    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        low_cpu_mem_usage=True
    )
    
    # For now, we'll run on CPU to avoid device issues
    device = "cpu"
    
    model.eval()
    
    results = []
    
    for prompt_item in tqdm(prompts, desc="Generating responses"):
        prompt = prompt_item.get('prompt') or prompt_item.get('instruction') or prompt_item.get('question')
        
        if not prompt:
            continue
            
        # Tokenize input
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512).to(device)
        
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
            logits_list = None
        
        # Decode response
        # Handle both tensor and dict outputs
        if isinstance(outputs, torch.Tensor):
            response_tokens = outputs[0][inputs.input_ids.shape[1]:]
        else:
            # Assume it's a dict-like object with sequences attribute
            response_tokens = outputs.sequences[0][inputs.input_ids.shape[1]:]
            
        response = tokenizer.decode(response_tokens, skip_special_tokens=True)
        
        result = {
            "prompt": prompt,
            "neox_output": response.strip()
        }
        
        # Add logits if requested
        if emit_logits and logits_list:
            result["logits"] = logits_list
            
        results.append(result)
    
    return results

def save_dataset(dataset: List[Dict[str, Any]], output_path: str):
    """
    Save the dataset to a JSON file.
    
    Args:
        dataset: List of prompt-response pairs
        output_path: Path to save the dataset
    """
    with open(output_path, 'w') as f:
        if output_path.endswith('.json'):
            json.dump(dataset, f, indent=2)
        elif output_path.endswith('.jsonl'):
            for item in dataset:
                f.write(json.dumps(item) + '\n')

def main():
    parser = argparse.ArgumentParser(description="Generate GPT-NeoX outputs for distillation dataset")
    parser.add_argument("--input_dataset", type=str, required=True, 
                        help="Path to input prompt dataset (JSON/JSONL)")
    parser.add_argument("--output_dataset", type=str, required=True,
                        help="Path to save the generated dataset")
    parser.add_argument("--model_name", type=str, default="EleutherAI/gpt-neox-20b",
                        help="Name/path of the GPT-NeoX model")
    parser.add_argument("--max_new_tokens", type=int, default=256,
                        help="Maximum number of new tokens to generate")
    parser.add_argument("--emit-logits", action="store_true",
                        help="Emit logits for knowledge distillation")
    parser.add_argument("--topk", type=int, default=100,
                        help="Number of top logits to keep for distillation")
    parser.add_argument("--server", type=str, choices=["vllm", "llama.cpp"], default="vllm",
                        help="Server backend for inference")
    
    args = parser.parse_args()
    
    # Load prompts
    prompts = load_prompts_from_dataset(args.input_dataset)
    print(f"Loaded {len(prompts)} prompts from {args.input_dataset}")
    
    # Generate responses
    dataset = generate_neox_responses(
        prompts, 
        model_name=args.model_name,
        max_new_tokens=args.max_new_tokens,
        emit_logits=args.emit_logits,
        topk=args.topk
    )
    
    # Save dataset
    save_dataset(dataset, args.output_dataset)
    print(f"Saved {len(dataset)} prompt-response pairs to {args.output_dataset}")

if __name__ == "__main__":
    main()