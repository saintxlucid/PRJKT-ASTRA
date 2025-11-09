#!/usr/bin/env python3
"""
ASTRA Dataset Integration System - Quick Start Guide

This script provides quick access to all dataset integration components.

Usage:
    python quick_start.py --help
    python quick_start.py --demo
    python quick_start.py --manager
    python quick_start.py --train
"""

import sys
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def print_banner():
    """Print welcome banner"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║              ASTRA Dataset Integration System - Quick Start                  ║
║                                                                              ║
║                    Project ASTRA_1.0 (ASTRA_CORE)                           ║
║          Advanced Structured Testing and Reasoning Assistant                ║
║                                                                              ║
║                       Created: October 18, 2025                              ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def demo_manager():
    """Demonstrate Dataset Manager"""
    print("\n" + "="*80)
    print("📊 DATASET MANAGER DEMO")
    print("="*80 + "\n")
    
    from tools.dataset_manager import get_dataset_manager
    
    dm = get_dataset_manager()
    dm.print_summary()
    
    print("\nAvailable subsystems:")
    for subsystem in dm.list_subsystems():
        print(f"  - {subsystem}")


def demo_loaders():
    """Demonstrate Data Loaders"""
    print("\n" + "="*80)
    print("📦 DATA LOADERS DEMO")
    print("="*80 + "\n")
    
    from tools.dataset_manager import get_dataset_manager
    from tools.data_loaders import get_loader
    
    dm = get_dataset_manager()
    
    # Load NLU dataset
    print("Loading IMDB dataset for NLU...")
    dataset = dm.get_dataset('imdb')
    
    if dataset:
        loader = get_loader('nlu', dataset, batch_size=32)
        stats = loader.get_dataset_stats()
        print(f"\nDataset Statistics:")
        for split, stat in stats.items():
            print(f"  {split}:")
            print(f"    - Examples: {stat['num_examples']}")
            print(f"    - Features: {stat['num_features']}")


def demo_evaluators():
    """Demonstrate Evaluators"""
    print("\n" + "="*80)
    print("📈 EVALUATORS DEMO")
    print("="*80 + "\n")
    
    from tools.evaluator import get_evaluator
    
    # NLU Evaluation
    print("NLU Evaluation Example:")
    nlu_eval = get_evaluator('nlu')
    predictions = ['intent_a', 'intent_b', 'intent_a']
    targets = ['intent_a', 'intent_b', 'intent_c']
    metrics = nlu_eval.evaluate(predictions, targets)
    print(f"  Accuracy: {metrics.accuracy:.4f}")
    print(f"  F1 Score: {metrics.f1_score:.4f}")
    
    # Safety Evaluation
    print("\nSafety Evaluation Example:")
    safety_eval = get_evaluator('safety')
    scores = [0.1, 0.8, 0.2, 0.9]
    labels = [0, 1, 0, 1]
    metrics = safety_eval.evaluate(scores, labels)
    print(f"  Precision: {metrics.precision:.4f}")
    print(f"  Recall: {metrics.recall:.4f}")
    print(f"  F1 Score: {metrics.f1_score:.4f}")


def demo_finetuning():
    """Demonstrate Fine-tuning"""
    print("\n" + "="*80)
    print("🎯 FINE-TUNING DEMO")
    print("="*80 + "\n")
    
    print("Available fine-tuning scripts:")
    print("  python scripts/finetune_nlu.py --help")
    print("  python scripts/finetune_nlu.py --dataset clinc150 --epochs 3")
    print("  python scripts/finetune_nlu.py --dataset imdb --batch_size 64")
    print("\nTemplates available for:")
    print("  - ASR (Automatic Speech Recognition)")
    print("  - Safety (Toxicity Detection)")
    print("  - Code (Code Generation)")
    print("  - QA (Question Answering)")


def demo_full():
    """Run full demonstration"""
    demo_manager()
    demo_loaders()
    demo_evaluators()
    demo_finetuning()


def main():
    """Main entry point"""
    print_banner()
    
    # Parse arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == '--demo':
            demo_full()
        elif command == '--manager':
            demo_manager()
        elif command == '--loaders':
            demo_loaders()
        elif command == '--evaluators':
            demo_evaluators()
        elif command == '--train':
            demo_finetuning()
        elif command in ['--help', '-h']:
            print_help()
        else:
            print(f"Unknown command: {command}")
            print_help()
    else:
        print_help()


def print_help():
    """Print help message"""
    print("""
Usage:
    python quick_start.py [COMMAND]

Commands:
    --demo           Run full demonstration
    --manager        Show dataset manager demo
    --loaders        Show data loaders demo
    --evaluators     Show evaluators demo
    --train          Show fine-tuning demo
    --help           Show this help message

Examples:
    python quick_start.py --demo
    python quick_start.py --manager
    python quick_start.py --evaluators

For more information, see:
    - DATASET_BOOTSTRAP_README.md
    - DATASET_INTEGRATION_ARCHITECTURE.md
    - ASTRA_CORE_INTEGRATION.md
    - DATASET_INTEGRATION_COMPLETE.md
    - DATASET_INTEGRATION_STATUS.md

Quick Links:
    Dataset Manager:    tools/dataset_manager.py
    Data Loaders:       tools/data_loaders.py
    Evaluators:         tools/evaluator.py
    Fine-tuning:        scripts/finetune_nlu.py
""")


if __name__ == "__main__":
    main()
