# ASTRA Dataset Integration Architecture

This document outlines the integration of the dataset bootstrap system with ASTRA Core subsystems.

## Overview

The dataset integration layer provides:
1. **Data Loaders**: Subsystem-specific data loading interfaces
2. **Dataset Slicing**: Dynamic preprocessing and slicing utilities
3. **Fine-tuning Scripts**: Model adaptation pipelines
4. **Evaluation Framework**: Performance assessment tools
5. **Subsystem Integration**: Direct ASTRA Core integration

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     ASTRA Core                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   ┌────────┐    ┌─────────┐    ┌──────────┐
   │Dataset │    │  Data   │    │Fine-tune │
   │Manager │───▶│ Loaders │───▶│ Scripts  │
   └────────┘    └─────────┘    └──────────┘
        │              │              │
        │              └──────┬───────┘
        │                     │
        ▼                     ▼
   ┌──────────┐         ┌──────────────┐
   │Subsystems│         │Evaluation    │
   │(ASR,NLU) │         │Framework     │
   └──────────┘         └──────────────┘
```

## Component Details

### 1. Dataset Manager (`tools/dataset_manager.py`)
- Central interface for dataset access
- Lazy loading and caching
- Subsystem-specific metadata

### 2. Data Loaders (`tools/data_loaders.py`)
- ASR Loader: Speech and audio processing
- NLU Loader: Text and intent classification
- Safety Loader: Toxicity and safety evaluation
- Code Loader: Code generation and completion
- QA Loader: Question-answering datasets

### 3. Dataset Slicing (`tools/dataset_slicer.py`)
- Dynamic slicing based on subsystem needs
- Preprocessing pipelines
- Cache management

### 4. Fine-tuning Scripts (`scripts/finetune_*.py`)
- Model adaptation for each subsystem
- Training loops with validation
- Checkpoint management

### 5. Evaluation Framework (`tools/evaluator.py`)
- Performance metrics for each subsystem
- Validation pipelines
- Reporting utilities

## Integration Points

### In `astra_core.py`
1. Initialize Dataset Manager during Phase 2
2. Pass dataset references to subsystems
3. Enable fine-tuning and evaluation during runtime

### In Subsystems
1. Load data through Dataset Manager
2. Use Data Loaders for preprocessing
3. Execute evaluation through Evaluation Framework

## Usage Examples

### Load Dataset
```python
from tools.dataset_manager import DatasetManager

dm = DatasetManager()
squad_data = dm.get_dataset('squad')
```

### Fine-tune Model
```python
python scripts/finetune_nlu.py --dataset clinc150 --epochs 5
```

### Evaluate Subsystem
```python
from tools.evaluator import Evaluator

evaluator = Evaluator()
metrics = evaluator.evaluate('nlu', model, test_data)
```

## Files to Create

1. `tools/dataset_manager.py` - Main dataset interface
2. `tools/data_loaders.py` - Subsystem-specific loaders
3. `tools/dataset_slicer.py` - Preprocessing utilities
4. `tools/evaluator.py` - Evaluation framework
5. `scripts/finetune_asr.py` - ASR fine-tuning
6. `scripts/finetune_nlu.py` - NLU fine-tuning
7. `scripts/finetune_safety.py` - Safety evaluator fine-tuning
8. `scripts/finetune_code.py` - Code generation fine-tuning
9. `scripts/finetune_qa.py` - QA fine-tuning
10. `astra_core_integration.md` - Integration guide

## Next Steps

1. Create Dataset Manager
2. Implement Data Loaders
3. Build Dataset Slicer
4. Create Evaluator
5. Develop Fine-tuning Scripts
6. Integrate with ASTRA Core
