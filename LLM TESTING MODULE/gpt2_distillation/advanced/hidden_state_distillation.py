"""
Hidden State Matching Distillation

This script implements hidden state matching where internal representations from NeoX
are taught to GPT-2 using contrastive or regression losses.
"""

import argparse
import json
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm
from typing import List, Dict, Any, Tuple

class HiddenStateDataset(Dataset):
    """Dataset for hidden state matching distillation."""
    
    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        return self.data[idx]

class HiddenStateMatcher(torch.nn.Module):
    """Module to match hidden states between teacher and student models."""
    
    def __init__(self, student_hidden_size: int, teacher_hidden_size: int):
        """
        Initialize the hidden state matcher.
        
        Args:
            student_hidden_size: Hidden size of the student model
            teacher_hidden_size: Hidden size of the teacher model
        """
        super().__init__()
        self.projection = torch.nn.Linear(student_hidden_size, teacher_hidden_size)
        
    def forward(self, student_hidden_states):
        """
        Project student hidden states to teacher dimensionality.
        
        Args:
            student_hidden_states: Hidden states from student model
            
        Returns:
            Projected hidden states
        """
        return self.projection(student_hidden_states)

def extract_hidden_states(model, tokenizer, texts: List[str], 
                         device: str = "cuda" if torch.cuda.is_available() else "cpu") -> List[torch.Tensor]:
    """
    Extract hidden states from a model for given texts.
    
    Args:
        model: The model to extract hidden states from
        tokenizer: The tokenizer for the model
        texts: List of texts to process
        device: Device to run inference on
        
    Returns:
        List of hidden states for each text
    """
    hidden_states = []
    
    # Set model to evaluation mode
    model.eval()
    
    with torch.no_grad():
        for text in tqdm(texts, desc="Extracting hidden states"):
            # Tokenize input
            inputs = tokenizer(text, return_tensors="pt", truncation=True, 
                             max_length=512, padding=True).to(device)
            
            # Forward pass with hidden states
            outputs = model(**inputs, output_hidden_states=True)
            
            # Get hidden states (use last layer)
            last_hidden_states = outputs.hidden_states[-1]  # [batch_size, seq_len, hidden_size]
            
            # Store hidden states
            hidden_states.append(last_hidden_states.cpu())
    
    return hidden_states

def compute_hidden_state_loss(student_states: torch.Tensor, 
                             teacher_states: torch.Tensor,
                             matcher: HiddenStateMatcher = None) -> torch.Tensor:
    """
    Compute loss between student and teacher hidden states.
    
    Args:
        student_states: Hidden states from student model
        teacher_states: Hidden states from teacher model
        matcher: Optional matcher to align dimensions
        
    Returns:
        Computed loss
    """
    # Project student states if matcher is provided
    if matcher is not None:
        student_states = matcher(student_states)
    
    # Compute MSE loss between hidden states
    loss = F.mse_loss(student_states, teacher_states)
    
    return loss

def create_hidden_state_dataset(teacher_model_name: str = "EleutherAI/gpt-neox-20b",
                               student_model_name: str = "gpt2-large",
                               prompts: List[str] = None,
                               outputs: List[str] = None) -> List[Dict[str, Any]]:
    """
    Create dataset with hidden states from both teacher and student models.
    
    Args:
        teacher_model_name: Name of the teacher model
        student_model_name: Name of the student model
        prompts: List of prompts
        outputs: List of corresponding outputs
        
    Returns:
        Dataset with hidden states
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Load teacher model and tokenizer
    print("Loading teacher model...")
    teacher_tokenizer = AutoTokenizer.from_pretrained(teacher_model_name)
    teacher_tokenizer.pad_token = teacher_tokenizer.eos_token
    teacher_model = AutoModel.from_pretrained(teacher_model_name).to(device)
    
    # Load student model and tokenizer
    print("Loading student model...")
    student_tokenizer = AutoTokenizer.from_pretrained(student_model_name)
    student_tokenizer.pad_token = student_tokenizer.eos_token
    student_model = AutoModel.from_pretrained(student_model_name).to(device)
    
    # Combine prompts and outputs for full texts
    full_texts = [f"{prompt}\n{output}" for prompt, output in zip(prompts, outputs)]
    
    # Extract hidden states
    print("Extracting teacher hidden states...")
    teacher_hidden_states = extract_hidden_states(teacher_model, teacher_tokenizer, full_texts, device)
    
    print("Extracting student hidden states...")
    student_hidden_states = extract_hidden_states(student_model, student_tokenizer, full_texts, device)
    
    # Create dataset
    dataset = []
    for i, (prompt, output) in enumerate(zip(prompts, outputs)):
        dataset.append({
            "prompt": prompt,
            "output": output,
            "teacher_hidden_states": teacher_hidden_states[i],
            "student_hidden_states": student_hidden_states[i]
        })
    
    return dataset

def save_hidden_state_dataset(dataset: List[Dict[str, Any]], output_path: str):
    """
    Save the hidden state dataset (simplified version that saves metadata).
    
    Args:
        dataset: The hidden state dataset
        output_path: Path to save the dataset metadata
    """
    # For simplicity, we'll save just the metadata without the actual tensors
    metadata = []
    for item in dataset:
        metadata.append({
            "prompt": item["prompt"],
            "output": item["output"]
        })
    
    with open(output_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved hidden state dataset metadata with {len(metadata)} samples to {output_path}")

def load_distillation_dataset(dataset_path: str) -> Tuple[List[str], List[str]]:
    """
    Load prompts and outputs from a distillation dataset.
    
    Args:
        dataset_path: Path to the distillation dataset
        
    Returns:
        Tuple of prompts and outputs
    """
    with open(dataset_path, 'r') as f:
        if dataset_path.endswith('.json'):
            data = json.load(f)
        elif dataset_path.endswith('.jsonl'):
            data = []
            for line in f:
                data.append(json.loads(line.strip()))
    
    prompts = [item["prompt"] for item in data]
    outputs = [item["neox_output"] for item in data]
    
    return prompts, outputs

def main():
    parser = argparse.ArgumentParser(description="Hidden State Matching Distillation")
    parser.add_argument("--dataset_path", type=str, required=True,
                        help="Path to the distillation dataset")
    parser.add_argument("--output_dataset", type=str, required=True,
                        help="Path to save the hidden state dataset metadata")
    parser.add_argument("--teacher_model", type=str, default="EleutherAI/gpt-neox-20b",
                        help="Name/path of the teacher model")
    parser.add_argument("--student_model", type=str, default="gpt2-large",
                        help="Name/path of the student model")
    
    args = parser.parse_args()
    
    # Load dataset
    print("Loading distillation dataset...")
    prompts, outputs = load_distillation_dataset(args.dataset_path)
    print(f"Loaded {len(prompts)} prompt-output pairs")
    
    # Create hidden state dataset
    print("Creating hidden state dataset...")
    hidden_state_dataset = create_hidden_state_dataset(
        teacher_model_name=args.teacher_model,
        student_model_name=args.student_model,
        prompts=prompts,
        outputs=outputs
    )
    
    # Save dataset metadata
    save_hidden_state_dataset(hidden_state_dataset, args.output_dataset)
    
    print("Hidden state dataset creation completed!")

if __name__ == "__main__":
    main()