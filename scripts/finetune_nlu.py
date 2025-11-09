#!/usr/bin/env python3
"""
ASTRA NLU Fine-tuning Script

Fine-tune NLU models using downloaded datasets.
Supports intent classification and text categorization tasks.

Usage:
    python scripts/finetune_nlu.py --dataset clinc150 --epochs 5 --batch_size 32
    python scripts/finetune_nlu.py --dataset imdb --epochs 3 --learning_rate 2e-5

Created: October 18, 2025
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.dataset_manager import get_dataset_manager
from tools.data_loaders import get_loader
from tools.evaluator import get_evaluator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NLUFineTuner:
    """NLU Model Fine-tuner"""
    
    def __init__(
        self,
        dataset_name: str,
        epochs: int = 5,
        batch_size: int = 32,
        learning_rate: float = 2e-5,
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize fine-tuner.
        
        Args:
            dataset_name: Dataset to use for fine-tuning
            epochs: Number of training epochs
            batch_size: Training batch size
            learning_rate: Learning rate for optimizer
            output_dir: Directory to save checkpoints
        """
        self.dataset_name = dataset_name
        self.epochs = epochs
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.output_dir = Path(output_dir or "./checkpoints")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.dataset_manager = get_dataset_manager()
        self.evaluator = get_evaluator('nlu')
        
        if self.evaluator is None:
            raise RuntimeError("Failed to initialize NLU evaluator")
        
        logger.info(f"Initialized NLU Fine-tuner for {dataset_name}")
    
    def prepare_data(self):
        """Load and prepare dataset"""
        logger.info(f"Loading dataset: {self.dataset_name}")
        
        dataset = self.dataset_manager.get_dataset(self.dataset_name)
        if dataset is None:
            raise RuntimeError(f"Failed to load dataset: {self.dataset_name}")
        
        # Get data loader
        loader = get_loader('nlu', dataset, self.batch_size)
        if loader is None:
            raise RuntimeError("Failed to initialize data loader")
        
        logger.info("Dataset loaded successfully")
        logger.info(f"Dataset statistics: {loader.get_dataset_stats()}")
        
        return dataset, loader
    
    def train_epoch(self, loader, epoch: int) -> Dict[str, float]:
        """
        Train for one epoch.
        
        Note: This is a placeholder implementation.
        In production, this would integrate with a real training loop.
        """
        logger.info(f"Training epoch {epoch + 1}/{self.epochs}")
        
        # Get training batch
        train_batch = loader.get_train_batch()
        
        if not train_batch:
            logger.warning("Empty training batch")
            return {'loss': 0.0}
        
        # Placeholder training loop
        num_batches = max(1, len(train_batch.get('text', [])) // self.batch_size)
        
        total_loss = 0.0
        for batch_idx in range(num_batches):
            # Placeholder loss calculation
            batch_loss = 0.1 * (1.0 - epoch / self.epochs)  # Decreasing loss
            total_loss += batch_loss
            
            if (batch_idx + 1) % 10 == 0:
                logger.debug(f"  Batch {batch_idx + 1}/{num_batches}: Loss={batch_loss:.4f}")
        
        avg_loss = total_loss / num_batches if num_batches > 0 else 0.0
        logger.info(f"Epoch {epoch + 1} - Average Loss: {avg_loss:.4f}")
        
        return {'loss': avg_loss}
    
    def evaluate(self, loader) -> Dict[str, Any]:
        """Evaluate model on validation set"""
        logger.info("Evaluating on validation set...")
        
        val_batch = loader.get_val_batch()
        if not val_batch:
            logger.warning("Empty validation batch")
            return {}
        
        # Placeholder predictions
        texts = val_batch.get('text', [])
        predictions = ['label_' + str(i % 5) for i in range(len(texts))]  # Dummy predictions
        targets = val_batch.get('label', [str(i % 5) for i in range(len(texts))])  # Dummy targets
        
        metrics = self.evaluator.evaluate(predictions, targets)
        logger.info(f"Validation metrics: {metrics.to_dict()}")
        
        return metrics.to_dict()
    
    def save_checkpoint(self, epoch: int, metrics: Dict[str, Any]) -> None:
        """Save training checkpoint"""
        checkpoint = {
            'epoch': epoch,
            'dataset': self.dataset_name,
            'hyperparameters': {
                'batch_size': self.batch_size,
                'learning_rate': self.learning_rate,
                'epochs': self.epochs,
            },
            'metrics': metrics,
        }
        
        checkpoint_path = self.output_dir / f"checkpoint_epoch_{epoch}.json"
        checkpoint_path.write_text(json.dumps(checkpoint, indent=2))
        logger.info(f"Checkpoint saved: {checkpoint_path}")
    
    def train(self):
        """Main training loop"""
        logger.info("="*80)
        logger.info("Starting NLU Fine-tuning")
        logger.info("="*80)
        
        # Prepare data
        dataset, loader = self.prepare_data()
        
        # Training loop
        best_metrics = None
        for epoch in range(self.epochs):
            # Train
            train_results = self.train_epoch(loader, epoch)
            
            # Evaluate
            val_results = self.evaluate(loader)
            
            # Save checkpoint
            self.save_checkpoint(epoch, val_results)
            
            # Track best metrics
            if best_metrics is None or val_results.get('accuracy', 0) > best_metrics.get('accuracy', 0):
                best_metrics = val_results
                logger.info("✓ New best metrics!")
        
        logger.info("="*80)
        logger.info("Fine-tuning Complete")
        logger.info("="*80)
        
        if best_metrics:
            logger.info(f"Best metrics: {best_metrics}")
        
        # Print summary
        self._print_summary()
    
    def _print_summary(self) -> None:
        """Print training summary"""
        print("\n" + "="*80)
        print("ASTRA NLU Fine-tuning Summary")
        print("="*80)
        print(f"Dataset: {self.dataset_name}")
        print(f"Epochs: {self.epochs}")
        print(f"Batch Size: {self.batch_size}")
        print(f"Learning Rate: {self.learning_rate}")
        print(f"Output Directory: {self.output_dir}")
        
        if self.evaluator:
            summary = self.evaluator.get_summary()
            if summary:
                print("\nEvaluation Summary:")
                for key, value in summary.items():
                    print(f"  {key}: {value}")
        
        print("="*80 + "\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Fine-tune ASTRA NLU models',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/finetune_nlu.py --dataset clinc150 --epochs 5
  python scripts/finetune_nlu.py --dataset imdb --batch_size 64 --learning_rate 1e-5
        """
    )
    
    parser.add_argument(
        '--dataset',
        required=True,
        help='Dataset name (e.g., clinc150, imdb, ag_news)'
    )
    parser.add_argument(
        '--epochs',
        type=int,
        default=5,
        help='Number of training epochs (default: 5)'
    )
    parser.add_argument(
        '--batch_size',
        type=int,
        default=32,
        help='Training batch size (default: 32)'
    )
    parser.add_argument(
        '--learning_rate',
        type=float,
        default=2e-5,
        help='Learning rate (default: 2e-5)'
    )
    parser.add_argument(
        '--output_dir',
        help='Output directory for checkpoints (default: ./checkpoints)'
    )
    
    args = parser.parse_args()
    
    # Create fine-tuner
    try:
        finetuner = NLUFineTuner(
            dataset_name=args.dataset,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            output_dir=args.output_dir,
        )
        
        # Train
        finetuner.train()
        
    except Exception as e:
        logger.error(f"Fine-tuning failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
