# ASTRA Dataset Integration Guide

This guide explains how to integrate the dataset bootstrap system with ASTRA Core subsystems.

## Quick Integration Summary

The dataset integration provides:
1. **Dataset Manager** - Central access point for all datasets
2. **Data Loaders** - Subsystem-specific data preprocessing
3. **Evaluators** - Performance metrics and evaluation
4. **Fine-tuning Scripts** - Model adaptation pipelines

## Step 1: Initialize Dataset Manager in ASTRA Core

In `astra_core.py`, add dataset initialization during Phase 2 (Memory Integration):

```python
async def phase_2_memory(self):
    """Phase 2: Initialize memory systems and datasets"""
    print("\n" + "━"*80)
    print("🧠 PHASE 2: MEMORY & DATASET INTEGRATION")
    print("━"*80)
    
    try:
        # ... existing memory code ...
        
        # Initialize Dataset Manager
        from tools.dataset_manager import get_dataset_manager
        self.dataset_manager = get_dataset_manager()
        
        print("✓ Dataset Manager initialized")
        self.dataset_manager.print_summary()
        
    except Exception as e:
        logger.error(f"Failed to initialize datasets: {e}")
        print(f"⚠ Dataset initialization failed: {e}")
```

## Step 2: Access Datasets in Subsystems

Each subsystem can access its datasets through the Dataset Manager:

### NLU Subsystem Example

```python
from tools.dataset_manager import get_dataset_manager
from tools.data_loaders import get_loader
from tools.evaluator import get_evaluator

# Get dataset manager
dm = get_dataset_manager()

# Get NLU-specific datasets
nlu_datasets = dm.get_datasets_for_subsystem('nlu')

# For each dataset, get the appropriate loader
for dataset_name, dataset in nlu_datasets.items():
    loader = get_loader('nlu', dataset, batch_size=32)
    
    # Get training batch
    train_batch = loader.get_train_batch()
    
    # Process batch...
```

### Safety Subsystem Example

```python
from tools.evaluator import get_evaluator

# Get safety evaluator
evaluator = get_evaluator('safety')

# Evaluate predictions
metrics = evaluator.evaluate(
    predictions=[0.2, 0.8, 0.1],  # Toxicity scores
    targets=[0, 1, 0]  # Labels
)

# Get metrics
print(f"Precision: {metrics.precision}")
print(f"Recall: {metrics.recall}")
print(f"F1 Score: {metrics.f1_score}")
```

## Step 3: Use Fine-tuning Scripts

Fine-tune models for specific subsystems:

### NLU Fine-tuning

```bash
python scripts/finetune_nlu.py --dataset clinc150 --epochs 5 --batch_size 32
```

Options:
- `--dataset`: Dataset name (clinc150, imdb, ag_news, snips_built_in_intents)
- `--epochs`: Number of training epochs
- `--batch_size`: Training batch size
- `--learning_rate`: Learning rate (default: 2e-5)
- `--output_dir`: Checkpoint directory

### Run Fine-tuning Programmatically

```python
from scripts.finetune_nlu import NLUFineTuner

finetuner = NLUFineTuner(
    dataset_name='clinc150',
    epochs=5,
    batch_size=32,
    learning_rate=2e-5,
)

finetuner.train()
```

## Step 4: Evaluate Subsystem Performance

### Programmatic Evaluation

```python
from tools.evaluator import get_evaluator
from tools.dataset_manager import get_dataset_manager

# Get evaluator
qa_evaluator = get_evaluator('qa')

# Get test dataset
dm = get_dataset_manager()
squad = dm.get_dataset('squad')

# Run predictions on test set
predictions = [...]  # Your model's predictions
targets = squad['validation']['answers']  # Ground truth

# Evaluate
metrics = qa_evaluator.evaluate(predictions, targets)

# Save results
qa_evaluator.save_results(
    metrics,
    output_path='evaluation_results.json'
)

# Print summary
print(qa_evaluator.get_summary())
```

## Component Reference

### Dataset Manager

```python
from tools.dataset_manager import get_dataset_manager

dm = get_dataset_manager()

# List all datasets
datasets = dm.list_datasets()

# List subsystems
subsystems = dm.list_subsystems()

# Get dataset for subsystem
nlu_datasets = dm.get_datasets_for_subsystem('nlu')

# Get specific dataset
squad = dm.get_dataset('squad')

# Get dataset info
info = dm.get_dataset_info('squad')

# Print summary
dm.print_summary()
```

### Data Loaders

```python
from tools.data_loaders import get_loader

# Get loader for subsystem
loader = get_loader('nlu', dataset, batch_size=32)

# Preprocess data
loader.preprocess()

# Get batches
train_batch = loader.get_train_batch()
val_batch = loader.get_val_batch()

# Get statistics
stats = loader.get_dataset_stats()
```

### Evaluators

```python
from tools.evaluator import get_evaluator

# Get evaluator
eval = get_evaluator('nlu')

# Evaluate
metrics = eval.evaluate(predictions, targets)

# Get metrics
metrics.accuracy
metrics.precision
metrics.recall
metrics.f1_score

# Get summary
summary = eval.get_summary()

# Save results
eval.save_results(metrics, 'results.json')
```

## Available Datasets

| Dataset | Subsystems | Size | Purpose |
|---------|-----------|------|---------|
| wikitext | Language Model | 1.1 MB | Text generation |
| imdb | NLU | 4.9 MB | Sentiment analysis |
| snips_built_in_intents | NLU | 0.0 MB | Intent classification |
| clinc150 | NLU | 0.3 MB | Intent classification |
| ag_news | NLU | 6.0 MB | Text classification |
| docvqa/funsd | Vision | 13.2 MB | Document understanding |
| allenai/real-toxicity-prompts | Safety | 8.5 MB | Toxicity detection |
| mbpp | Code | 0.1 MB | Code generation |
| squad | QA | 4.0 MB | Question answering |

## Subsystem-Dataset Mapping

### NLU Subsystem
- imdb
- snips_built_in_intents
- clinc150
- ag_news

### Safety Subsystem
- allenai/real-toxicity-prompts

### Code Subsystem
- mbpp

### QA Subsystem
- squad

### Vision Subsystem
- docvqa/funsd

### Language Model
- wikitext

## Best Practices

1. **Lazy Loading**: Use `dm.get_dataset(name)` for automatic caching
2. **Batch Processing**: Use data loaders for proper preprocessing
3. **Validation**: Always evaluate on validation split
4. **Checkpointing**: Save checkpoints during training
5. **Error Handling**: Catch exceptions when loading datasets

## Troubleshooting

### Dataset Not Found

```python
# Check available datasets
available = dm.list_datasets()
print(available)

# Get dataset info
info = dm.get_dataset_info('dataset_name')
```

### Data Loading Issues

```python
# Check dataset statistics
stats = loader.get_dataset_stats()
print(stats)

# Verify dataset path
metadata = dm.get_metadata('dataset_name')
print(metadata.path)
```

### Evaluation Metrics

```python
# Get evaluation summary
summary = evaluator.get_summary()

# Check history
history = evaluator.metrics_history

# Save detailed results
evaluator.save_results(metrics, 'results.json')
```

## Next Steps

1. Integrate Dataset Manager into ASTRA Core initialization
2. Update subsystems to use Dataset Manager
3. Run fine-tuning scripts for target subsystems
4. Evaluate subsystem performance
5. Monitor training with evaluation metrics

## Support

For issues or questions:
- Check `DATASET_BOOTSTRAP_README.md` for dataset setup
- Review tool documentation in `tools/` directory
- Check script examples in `scripts/` directory
