"""
Experiment Runner: Automate Distillation Experiments

This script automates the process of running multiple distillation experiments
and comparing their results.
"""

import argparse
import os
import json
import subprocess
import sys
from typing import Dict, List, Any, Optional

def run_command(command: str, cwd: Optional[str] = None) -> bool:
    """
    Run a command and return success status.
    
    Args:
        command: Command to run
        cwd: Working directory
        
    Returns:
        True if command succeeded, False otherwise
    """
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            print(f"Error running command: {command}")
            print(f"stderr: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"Exception running command: {command}")
        print(f"Error: {e}")
        return False

def create_sample_dataset(output_path: str):
    """
    Create a sample dataset for experiments.
    
    Args:
        output_path: Path to save the sample dataset
    """
    sample_data = [
        {
            "prompt": "Explain the concept of photosynthesis.",
            "neox_output": "Photosynthesis is the process by which plants convert light energy into chemical energy. During this process, plants use sunlight, carbon dioxide from the air, and water from the soil to produce glucose and oxygen. The glucose serves as an energy source for the plant, while oxygen is released into the atmosphere as a byproduct."
        },
        {
            "prompt": "What are the main differences between renewable and non-renewable energy sources?",
            "neox_output": "Renewable energy sources are naturally replenished on a human timescale, such as solar, wind, hydroelectric, and geothermal energy. Non-renewable energy sources exist in finite quantities and cannot be replenished in a short period, such as fossil fuels (coal, oil, natural gas) and nuclear fuel. Renewable sources are generally more environmentally friendly, while non-renewable sources often have higher energy density."
        },
        {
            "prompt": "Describe the water cycle.",
            "neox_output": "The water cycle, also known as the hydrological cycle, is the continuous movement of water on, above, and below the surface of the Earth. It involves several key processes: evaporation (water turning into vapor), condensation (vapor turning into droplets), precipitation (rain, snow, sleet, or hail falling to the ground), and collection (water gathering in bodies like rivers, lakes, and oceans). This cycle is essential for maintaining life on Earth."
        }
    ]
    
    with open(output_path, 'w') as f:
        json.dump(sample_data, f, indent=2)
    print(f"Sample dataset created at {output_path}")

def run_basic_distillation(data_path: str, output_dir: str) -> bool:
    """
    Run basic distillation experiment.
    
    Args:
        data_path: Path to distillation dataset
        output_dir: Output directory for trained model
        
    Returns:
        True if successful, False otherwise
    """
    command = (
        f"python scripts/train_gpt2_distilled.py "
        f"--dataset_path {data_path} "
        f"--output_dir {output_dir} "
        f"--model_name gpt2 "
        f"--per_device_train_batch_size 2 "
        f"--gradient_accumulation_steps 4 "
        f"--learning_rate 5e-5 "
        f"--num_train_epochs 1"  # Reduced for quick testing
    )
    
    print(f"Running basic distillation: {command}")
    return run_command(command)

def run_lora_distillation(data_path: str, output_dir: str) -> bool:
    """
    Run LoRA distillation experiment.
    
    Args:
        data_path: Path to distillation dataset
        output_dir: Output directory for trained model
        
    Returns:
        True if successful, False otherwise
    """
    command = (
        f"python advanced/lora_distillation.py "
        f"--dataset_path {data_path} "
        f"--output_dir {output_dir} "
        f"--model_name gpt2 "
        f"--per_device_train_batch_size 4 "
        f"--gradient_accumulation_steps 2 "
        f"--learning_rate 1e-4 "
        f"--num_train_epochs 1"  # Reduced for quick testing
    )
    
    print(f"Running LoRA distillation: {command}")
    return run_command(command)

def run_cot_distillation(prompt_path: str, output_dir: str) -> bool:
    """
    Run CoT distillation experiment.
    
    Args:
        prompt_path: Path to prompt dataset
        output_dir: Output directory for CoT dataset
        
    Returns:
        True if successful, False otherwise
    """
    cot_dataset_path = f"{output_dir}/cot_dataset.json"
    
    command = (
        f"python advanced/cot_distillation.py "
        f"--prompt_file {prompt_path} "
        f"--output_dataset {cot_dataset_path} "
        f"--model_name gpt2 "
        f"--max_new_tokens 128"  # Reduced for quick testing
    )
    
    print(f"Running CoT distillation: {command}")
    return run_command(command)

def compare_models(model_paths: List[str], model_names: List[str], test_dataset: str) -> str:
    """
    Compare models and generate results.
    
    Args:
        model_paths: List of model paths
        model_names: List of model names
        test_dataset: Path to test dataset
        
    Returns:
        Path to results file
    """
    # Build command
    model_args = " ".join([f"--models {path}" for path in model_paths])
    name_args = " ".join([f"--names {name}" for name in model_names])
    
    results_file = "experiment_results.csv"
    command = (
        f"python experiments/compare_distillation_methods.py "
        f"{model_args} {name_args} "
        f"--test_dataset {test_dataset} "
        f"--output_file {results_file}"
    )
    
    print(f"Comparing models: {command}")
    if run_command(command):
        return results_file
    return ""  # Return empty string instead of None

def generate_report(results_file: str) -> bool:
    """
    Generate experiment report.
    
    Args:
        results_file: Path to results file
        
    Returns:
        True if successful, False otherwise
    """
    command = (
        f"python experiments/generate_report.py "
        f"--results_file {results_file} "
        f"--report_file distillation_experiment_report.md "
        f"--plot_file performance_comparison.png"
    )
    
    print(f"Generating report: {command}")
    return run_command(command)

def main():
    parser = argparse.ArgumentParser(description="Run Distillation Experiments")
    parser.add_argument("--experiment_dir", type=str, default="experiments/results",
                        help="Directory to store experiment results")
    parser.add_argument("--data_path", type=str, default="data/sample_prompts.json",
                        help="Path to prompt dataset")
    parser.add_argument("--run_basic", action="store_true",
                        help="Run basic distillation experiment")
    parser.add_argument("--run_lora", action="store_true",
                        help="Run LoRA distillation experiment")
    parser.add_argument("--run_cot", action="store_true",
                        help="Run CoT distillation experiment")
    parser.add_argument("--compare", action="store_true",
                        help="Compare trained models")
    parser.add_argument("--report", action="store_true",
                        help="Generate experiment report")
    
    args = parser.parse_args()
    
    # Create experiment directory
    os.makedirs(args.experiment_dir, exist_ok=True)
    
    # Create sample dataset if needed
    distillation_dataset = f"{args.experiment_dir}/distillation_dataset.json"
    if not os.path.exists(distillation_dataset):
        create_sample_dataset(distillation_dataset)
    
    # Track trained models
    trained_models = []
    model_names = []
    
    # Run experiments
    if args.run_basic:
        model_path = f"{args.experiment_dir}/basic_distillation"
        if run_basic_distillation(distillation_dataset, model_path):
            trained_models.append(model_path)
            model_names.append("Basic Distillation")
        else:
            print("Basic distillation failed!")
    
    if args.run_lora:
        model_path = f"{args.experiment_dir}/lora_distillation"
        if run_lora_distillation(distillation_dataset, model_path):
            trained_models.append(model_path)
            model_names.append("LoRA Distillation")
        else:
            print("LoRA distillation failed!")
    
    if args.run_cot:
        # For CoT, we just generate the dataset
        cot_output = f"{args.experiment_dir}/cot_experiment"
        if run_cot_distillation(args.data_path, cot_output):
            print("CoT distillation dataset generated successfully!")
            # For a full experiment, we would train on this dataset
        else:
            print("CoT distillation failed!")
    
    # Compare models
    if args.compare and trained_models:
        results_file = compare_models(trained_models, model_names, distillation_dataset)
        if results_file and args.report:
            generate_report(results_file)
    
    print("\nExperiment runner completed!")

if __name__ == "__main__":
    main()