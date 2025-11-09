"""
Multi-Task Distillation: Combine different tasks in dataset

This script creates a multi-task distillation dataset that combines different types of tasks
(QA, CoT, summarization, reasoning) with task-conditioned prompts.
"""

import json
import random
from typing import List, Dict, Any, Optional

# Task templates for different types of tasks
TASK_TEMPLATES = {
    "qa": {
        "prompt_template": "### Question:\n{input}\n\n### Answer:",
        "description": "Question Answering task"
    },
    "cot": {
        "prompt_template": "### Problem:\n{input}\n\n### Solution:\nLet's think step by step.",
        "description": "Chain-of-Thought reasoning task"
    },
    "summarization": {
        "prompt_template": "### Document:\n{input}\n\n### Summary:",
        "description": "Text summarization task"
    },
    "translation": {
        "prompt_template": "### Translate from English to French:\n{input}\n\n### French:",
        "description": "Language translation task"
    },
    "classification": {
        "prompt_template": "### Text:\n{input}\n\n### Sentiment (positive/negative):",
        "description": "Text classification task"
    }
}

def create_multi_task_prompt(prompt: str, task_type: str) -> str:
    """
    Create a task-conditioned prompt based on the task type.
    
    Args:
        prompt: The original prompt
        task_type: Type of task (qa, cot, summarization, etc.)
        
    Returns:
        Task-conditioned prompt
    """
    if task_type in TASK_TEMPLATES:
        return TASK_TEMPLATES[task_type]["prompt_template"].format(input=prompt)
    else:
        # Default to QA format if task type is unknown
        return f"### Task: {task_type}\n{prompt}\n\n### Response:"

def convert_to_multi_task_dataset(dataset: List[Dict[str, str]], 
                                 task_distribution: Optional[Dict[str, float]] = None) -> List[Dict[str, str]]:
    """
    Convert a single-task dataset to a multi-task dataset by adding task conditioning.
    
    Args:
        dataset: Original dataset with prompt/neox_output pairs
        task_distribution: Distribution of task types (default is uniform)
        
    Returns:
        Multi-task dataset with task-conditioned prompts
    """
    if task_distribution is None:
        # Default uniform distribution
        task_types = list(TASK_TEMPLATES.keys())
        task_distribution = {task_type: 1.0/len(task_types) for task_type in task_types}
    
    # Normalize distribution
    total = sum(task_distribution.values())
    task_distribution = {k: v/total for k, v in task_distribution.items()}
    
    # Convert dataset
    multi_task_dataset = []
    for item in dataset:
        # Sample a task type based on distribution
        task_type = random.choices(
            list(task_distribution.keys()), 
            weights=list(task_distribution.values())
        )[0]
        
        # Create task-conditioned prompt
        task_conditioned_prompt = create_multi_task_prompt(item["prompt"], task_type)
        
        # Add to multi-task dataset
        multi_task_dataset.append({
            "original_prompt": item["prompt"],
            "task_type": task_type,
            "prompt": task_conditioned_prompt,
            "neox_output": item["neox_output"]
        })
    
    return multi_task_dataset

def load_dataset(dataset_path: str) -> List[Dict[str, str]]:
    """
    Load dataset from JSON/JSONL file.
    
    Args:
        dataset_path: Path to the dataset file
        
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
    return []  # Return empty list if file type is not recognized

def save_dataset(dataset: List[Dict[str, str]], output_path: str):
    """
    Save dataset to JSON file.
    
    Args:
        dataset: Dataset to save
        output_path: Path to save the dataset
    """
    with open(output_path, 'w') as f:
        json.dump(dataset, f, indent=2)

def generate_sample_multi_task_dataset() -> List[Dict[str, str]]:
    """
    Generate a sample multi-task dataset for demonstration.
    
    Returns:
        Sample multi-task dataset
    """
    sample_prompts = [
        "What is the capital of France?",
        "If a train leaves station A at 60 mph and another leaves station B at 40 mph, when do they meet?",
        "Summarize the following article about climate change...",
        "Translate 'Hello, how are you?' to Spanish",
        "This movie was fantastic! I loved every minute of it."
    ]
    
    sample_outputs = [
        "The capital of France is Paris.",
        "To solve this problem, we need to know the distance between the stations. Let's assume the distance is D miles. The trains approach each other at a combined speed of 60 + 40 = 100 mph. Time to meet = D/100 hours.",
        "Climate change refers to long-term shifts in global temperatures and weather patterns. While climate change can occur naturally, human activities have been the main driver of climate change since the 1800s.",
        "Hola, ¿cómo estás?",
        "positive"
    ]
    
    # Create dataset
    dataset = [{"prompt": prompt, "neox_output": output} 
               for prompt, output in zip(sample_prompts, sample_outputs)]
    
    # Convert to multi-task dataset
    return convert_to_multi_task_dataset(dataset)

def main():
    """Example usage of multi-task distillation."""
    print("Multi-Task Distillation Example")
    print("=" * 40)
    
    # Generate sample dataset
    sample_dataset = generate_sample_multi_task_dataset()
    
    print(f"Generated {len(sample_dataset)} multi-task samples:")
    for i, item in enumerate(sample_dataset[:3]):  # Show first 3 samples
        print(f"\nSample {i+1}:")
        print(f"Task Type: {item['task_type']}")
        print(f"Prompt: {item['prompt']}")
        print(f"Output: {item['neox_output']}")
    
    # Save sample dataset
    save_dataset(sample_dataset, "sample_multi_task_dataset.json")
    print("\nSample dataset saved to sample_multi_task_dataset.json")
    
    # Example of custom task distribution
    print("\n" + "=" * 40)
    print("Custom Task Distribution Example")
    
    custom_distribution = {
        "qa": 0.4,        # 40% QA tasks
        "cot": 0.3,       # 30% Chain-of-Thought tasks
        "summarization": 0.2,  # 20% Summarization tasks
        "translation": 0.1   # 10% Translation tasks
    }
    
    # Convert with custom distribution
    custom_dataset = convert_to_multi_task_dataset(sample_dataset[:5], custom_distribution)
    
    print("Task distribution:")
    for task_type, weight in custom_distribution.items():
        count = sum(1 for item in custom_dataset if item["task_type"] == task_type)
        print(f"  {task_type}: {count}/{len(custom_dataset)} ({weight*100:.1f}%)")

if __name__ == "__main__":
    main()