# ASTRA Dataset Integration System - Complete Summary

## Overview

The ASTRA Dataset Integration System provides a complete infrastructure for managing, loading, fine-tuning, and evaluating models using downloaded datasets. This system bridges the dataset bootstrap layer with ASTRA Core subsystems.

## Components Created

### 1. Dataset Manager (`tools/dataset_manager.py`)
**Purpose**: Central interface for dataset access and management

**Features**:
- Lazy loading with automatic caching
- Subsystem-to-dataset mapping
- Dataset metadata and size tracking
- Manifest validation and loading
- Singleton pattern for global access

**Key Classes**:
- `DatasetMetadata` - Metadata container for datasets
- `DatasetManager` - Main dataset management interface

**Usage**:
```python
from tools.dataset_manager import get_dataset_manager

dm = get_dataset_manager()
squad_data = dm.get_dataset('squad')
nlu_datasets = dm.get_datasets_for_subsystem('nlu')
```

### 2. Data Loaders (`tools/data_loaders.py`)
**Purpose**: Subsystem-specific data preprocessing and batching

**Features**:
- Base loader interface (ABC)
- Subsystem-specific loaders (NLU, ASR, Safety, Code, QA)
- Preprocessing pipelines
- Batch generation
- Dataset statistics

**Available Loaders**:
- `ASRDataLoader` - Audio processing for speech recognition
- `NLUDataLoader` - Text processing for natural language understanding
- `SafetyDataLoader` - Text processing for toxicity detection
- `CodeDataLoader` - Code processing for code generation
- `QADataLoader` - QA data processing for reading comprehension

**Usage**:
```python
from tools.data_loaders import get_loader

loader = get_loader('nlu', dataset, batch_size=32)
train_batch = loader.get_train_batch()
val_batch = loader.get_val_batch()
```

### 3. Evaluator Framework (`tools/evaluator.py`)
**Purpose**: Performance metrics and evaluation pipelines

**Features**:
- Base evaluator class (ABC)
- Subsystem-specific evaluators
- Standard metrics (accuracy, precision, recall, F1)
- Custom metrics support
- Results persistence

**Available Evaluators**:
- `NLUEvaluator` - Intent classification accuracy
- `SafetyEvaluator` - Toxicity detection (precision, recall, F1)
- `CodeEvaluator` - Code generation exact match
- `QAEvaluator` - QA performance (EM, F1)
- `ASREvaluator` - Speech recognition (WER)

**Usage**:
```python
from tools.evaluator import get_evaluator

evaluator = get_evaluator('nlu')
metrics = evaluator.evaluate(predictions, targets)
print(metrics.accuracy, metrics.f1_score)
```

### 4. Fine-tuning Scripts

#### NLU Fine-tuning (`scripts/finetune_nlu.py`)
**Purpose**: Fine-tune NLU models using downloaded datasets

**Features**:
- Configurable training loop
- Epoch-based training with validation
- Checkpoint management
- Automatic evaluation
- CLI interface

**Usage**:
```bash
python scripts/finetune_nlu.py --dataset clinc150 --epochs 5 --batch_size 32
python scripts/finetune_nlu.py --dataset imdb --learning_rate 2e-5
```

**CLI Arguments**:
- `--dataset` (required): Dataset name
- `--epochs`: Number of training epochs (default: 5)
- `--batch_size`: Training batch size (default: 32)
- `--learning_rate`: Learning rate (default: 2e-5)
- `--output_dir`: Checkpoint directory (default: ./checkpoints)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   ASTRA Core                            │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Phase 2: Memory & Datasets               │  │
│  │         - Initialize Dataset Manager             │  │
│  │         - Load dataset metadata                  │  │
│  │         - Register subsystems                    │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
   ┌─────────┐ ┌────────┐ ┌──────────┐
   │Dataset  │ │  Data  │ │Fine-tune │
   │Manager  │ │ Loaders│ │ Scripts  │
   └─────────┘ └────────┘ └──────────┘
        │          │          │
        └──────────┼──────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │    Evaluator         │
        │  Framework           │
        └──────────────────────┘
```

## Integration with ASTRA Core

### Step 1: Initialize in Phase 2

In `astra_core.py`, modify `phase_2_memory()`:

```python
async def phase_2_memory(self):
    # ... existing code ...
    
    from tools.dataset_manager import get_dataset_manager
    
    self.dataset_manager = get_dataset_manager()
    print("✓ Dataset Manager initialized")
    self.dataset_manager.print_summary()
```

### Step 2: Use in Subsystems

Each subsystem can access datasets:

```python
dm = get_dataset_manager()
subsystem_datasets = dm.get_datasets_for_subsystem('nlu')

for name, dataset in subsystem_datasets.items():
    loader = get_loader('nlu', dataset)
    train_batch = loader.get_train_batch()
    # Process...
```

### Step 3: Evaluate Performance

```python
evaluator = get_evaluator('nlu')
metrics = evaluator.evaluate(predictions, targets)
evaluator.save_results(metrics, f'results_{name}.json')
```

## Datasets & Subsystem Mapping

| Dataset | Size | Subsystems | Purpose |
|---------|------|-----------|---------|
| wikitext | 1.1 MB | Language Model | Text generation training |
| imdb | 4.9 MB | NLU | Sentiment classification |
| snips_built_in_intents | 0.0 MB | NLU | Intent classification |
| clinc150 | 0.3 MB | NLU | Intent classification |
| ag_news | 6.0 MB | NLU | Text categorization |
| docvqa/funsd | 13.2 MB | Vision | Document understanding |
| allenai/real-toxicity-prompts | 8.5 MB | Safety | Toxicity detection |
| mbpp | 0.1 MB | Code | Code generation |
| squad | 4.0 MB | QA | Reading comprehension |

**Total Size**: ~38.1 MB

## File Structure

```
.
├── tools/
│   ├── bootstrap_datasets.py      # Dataset downloader
│   ├── dataset_manager.py         # Central dataset interface
│   ├── data_loaders.py            # Subsystem-specific loaders
│   └── evaluator.py               # Evaluation framework
│
├── scripts/
│   ├── bootstrap_datasets.py      # (existing)
│   ├── verify_downloads.py        # (existing)
│   ├── finetune_nlu.py            # NLU fine-tuning
│   ├── finetune_asr.py            # (template)
│   ├── finetune_safety.py         # (template)
│   ├── finetune_code.py           # (template)
│   └── finetune_qa.py             # (template)
│
├── data/
│   ├── wikitext/
│   ├── imdb/
│   ├── clinc150/
│   ├── ag_news/
│   ├── snips_built_in_intents/
│   ├── funsd/
│   ├── real_toxicity_prompts/
│   ├── mbpp/
│   ├── squad/
│   └── _manifest.json
│
├── DATASET_BOOTSTRAP_README.md               # Dataset setup guide
├── DATASET_INTEGRATION_ARCHITECTURE.md       # System architecture
├── ASTRA_CORE_INTEGRATION.md                 # Integration guide
└── astra_core.py                             # (modified for dataset integration)
```

## Key Features

### 1. Central Dataset Management
- Single point of access for all datasets
- Automatic caching and lazy loading
- Metadata tracking

### 2. Subsystem-Specific Processing
- Tailored data loaders for each subsystem
- Proper preprocessing for domain-specific needs
- Batch generation and statistics

### 3. Comprehensive Evaluation
- Multiple evaluation metrics per subsystem
- History tracking and summary statistics
- Result persistence for analysis

### 4. Production-Ready Fine-tuning
- Configurable training loops
- Checkpoint management
- Hyperparameter control

## Usage Examples

### Load and Use Dataset

```python
from tools.dataset_manager import get_dataset_manager
from tools.data_loaders import get_loader

dm = get_dataset_manager()
dataset = dm.get_dataset('imdb')
loader = get_loader('nlu', dataset, batch_size=32)

# Get training batch
train_batch = loader.get_train_batch()
print(f"Batch texts: {len(train_batch['text'])}")
```

### Evaluate Model

```python
from tools.evaluator import get_evaluator

evaluator = get_evaluator('nlu')

predictions = ['positive', 'negative', 'positive']
targets = ['positive', 'negative', 'neutral']

metrics = evaluator.evaluate(predictions, targets)
print(f"Accuracy: {metrics.accuracy:.4f}")
print(f"F1 Score: {metrics.f1_score:.4f}")
```

### Fine-tune Model

```bash
# Command line
python scripts/finetune_nlu.py --dataset clinc150 --epochs 3

# Or programmatically
from scripts.finetune_nlu import NLUFineTuner

trainer = NLUFineTuner(dataset_name='clinc150', epochs=3)
trainer.train()
```

## Performance Considerations

1. **Memory**: Datasets are loaded on-demand and cached
2. **Speed**: Lazy loading reduces initialization time
3. **Storage**: ~38 MB total dataset size
4. **Scalability**: Easily extensible for new datasets and subsystems

## Future Enhancements

1. Create fine-tuning scripts for remaining subsystems (ASR, Safety, Code, QA)
2. Add advanced preprocessing pipelines (tokenization, normalization)
3. Implement distributed training support
4. Add cross-validation utilities
5. Create visualization tools for results
6. Add data augmentation techniques
7. Implement active learning strategies

## Testing

All components include test code at the module level:

```bash
# Test Dataset Manager
python tools/dataset_manager.py

# Test Data Loaders
python tools/data_loaders.py

# Test Evaluators
python tools/evaluator.py
```

## Support Documents

1. **DATASET_BOOTSTRAP_README.md** - Dataset setup and management
2. **DATASET_INTEGRATION_ARCHITECTURE.md** - System design
3. **ASTRA_CORE_INTEGRATION.md** - Integration patterns and examples

## Status

✅ **Complete**: Dataset Manager, Data Loaders, Evaluators
✅ **Complete**: NLU Fine-tuning Script
⏳ **Templates Created**: ASR, Safety, Code, QA Fine-tuning Scripts
🔄 **Ready for Integration**: All components ready for ASTRA Core

## Next Steps

1. Integrate Dataset Manager into ASTRA Core initialization
2. Update subsystems to use data loaders
3. Configure and run fine-tuning scripts
4. Implement cross-subsystem evaluation
5. Add monitoring and logging
6. Create performance dashboards
