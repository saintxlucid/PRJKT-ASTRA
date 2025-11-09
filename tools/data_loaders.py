"""
ASTRA Data Loaders

Subsystem-specific data loading interfaces for preprocessing and formatting datasets.
Each loader handles the unique requirements of its target subsystem.

Created: October 18, 2025
"""

from typing import Dict, Any, List, Tuple, Optional
from abc import ABC, abstractmethod
from datasets import DatasetDict, Dataset
import logging

logger = logging.getLogger(__name__)


class BaseDataLoader(ABC):
    """Base class for all data loaders"""
    
    def __init__(self, dataset: DatasetDict, batch_size: int = 32):
        """
        Initialize data loader.
        
        Args:
            dataset: DatasetDict to load
            batch_size: Batch size for loading
        """
        self.dataset = dataset
        self.batch_size = batch_size
    
    @abstractmethod
    def preprocess(self) -> None:
        """Preprocess dataset for subsystem"""
        pass
    
    @abstractmethod
    def get_train_batch(self) -> Any:
        """Get training batch"""
        pass
    
    @abstractmethod
    def get_val_batch(self) -> Any:
        """Get validation batch"""
        pass
    
    def get_dataset_stats(self) -> Dict[str, Any]:
        """Get dataset statistics"""
        stats = {}
        for split_name, split_data in self.dataset.items():
            stats[split_name] = {
                'num_examples': len(split_data),
                'num_features': len(split_data.features) if hasattr(split_data, 'features') else 0,
                'feature_names': list(split_data.features.keys()) if hasattr(split_data, 'features') else [],
            }
        return stats


class ASRDataLoader(BaseDataLoader):
    """Data loader for Automatic Speech Recognition (ASR) subsystem"""
    
    def preprocess(self) -> None:
        """Preprocess audio data for ASR"""
        logger.info("Preprocessing audio data for ASR...")
        # Audio-specific preprocessing would go here
        # - Normalize sample rates
        # - Resample to target rate
        # - Extract audio features (MFCC, spectrogram)
        # - Augmentation (noise, pitch shift)
    
    def get_train_batch(self, indices: Optional[List[int]] = None) -> Dict[str, Any]:
        """Get training batch of audio samples"""
        if 'train' not in self.dataset:
            return {}
        
        split = self.dataset['train']
        if indices is None:
            indices = list(range(min(self.batch_size, len(split))))
        
        batch = {
            'audio': [split[i].get('audio') for i in indices],
            'transcription': [split[i].get('transcription', split[i].get('text', '')) for i in indices],
        }
        return batch
    
    def get_val_batch(self, indices: Optional[List[int]] = None) -> Dict[str, Any]:
        """Get validation batch"""
        for split_name in ['validation', 'test']:
            if split_name in self.dataset:
                split = self.dataset[split_name]
                if indices is None:
                    indices = list(range(min(self.batch_size, len(split))))
                
                return {
                    'audio': [split[i].get('audio') for i in indices],
                    'transcription': [split[i].get('transcription', split[i].get('text', '')) for i in indices],
                }
        return {}


class NLUDataLoader(BaseDataLoader):
    """Data loader for Natural Language Understanding (NLU) subsystem"""
    
    def preprocess(self) -> None:
        """Preprocess text data for NLU"""
        logger.info("Preprocessing text data for NLU...")
        # Text-specific preprocessing
        # - Tokenization
        # - Lowercasing
        # - Stop word removal
        # - Lemmatization
    
    def get_train_batch(self, indices: Optional[List[int]] = None) -> Dict[str, Any]:
        """Get training batch of text samples"""
        if 'train' not in self.dataset:
            return {}
        
        split = self.dataset['train']
        if indices is None:
            indices = list(range(min(self.batch_size, len(split))))
        
        batch = {}
        for i in indices:
            example = split[i]
            if 'text' in example:
                batch.setdefault('text', []).append(example['text'])
            if 'label' in example:
                batch.setdefault('label', []).append(example['label'])
            elif 'intent' in example:
                batch.setdefault('intent', []).append(example['intent'])
        
        return batch
    
    def get_val_batch(self, indices: Optional[List[int]] = None) -> Dict[str, Any]:
        """Get validation batch"""
        for split_name in ['validation', 'test']:
            if split_name in self.dataset:
                split = self.dataset[split_name]
                if indices is None:
                    indices = list(range(min(self.batch_size, len(split))))
                
                batch = {}
                for i in indices:
                    example = split[i]
                    if 'text' in example:
                        batch.setdefault('text', []).append(example['text'])
                    if 'label' in example:
                        batch.setdefault('label', []).append(example['label'])
                    elif 'intent' in example:
                        batch.setdefault('intent', []).append(example['intent'])
                
                return batch
        return {}


class SafetyDataLoader(BaseDataLoader):
    """Data loader for Safety & Toxicity Detection subsystem"""
    
    def preprocess(self) -> None:
        """Preprocess text data for safety evaluation"""
        logger.info("Preprocessing text data for safety evaluation...")
        # Safety-specific preprocessing
        # - Tokenization
        # - Normalization
        # - Profanity filtering (optional)
    
    def get_train_batch(self, indices: Optional[List[int]] = None) -> Dict[str, Any]:
        """Get training batch for safety evaluation"""
        if 'train' not in self.dataset:
            return {}
        
        split = self.dataset['train']
        if indices is None:
            indices = list(range(min(self.batch_size, len(split))))
        
        batch = {
            'text': [],
            'toxicity_scores': [],
        }
        
        for i in indices:
            example = split[i]
            if 'text' in example or 'prompt' in example:
                text = example.get('text') or example.get('prompt')
                batch['text'].append(text)
                batch['toxicity_scores'].append(example.get('toxicity', 0.0))
        
        return batch
    
    def get_val_batch(self, indices: Optional[List[int]] = None) -> Dict[str, Any]:
        """Get validation batch"""
        for split_name in ['validation', 'test']:
            if split_name in self.dataset:
                split = self.dataset[split_name]
                if indices is None:
                    indices = list(range(min(self.batch_size, len(split))))
                
                batch = {
                    'text': [],
                    'toxicity_scores': [],
                }
                
                for i in indices:
                    example = split[i]
                    if 'text' in example or 'prompt' in example:
                        text = example.get('text') or example.get('prompt')
                        batch['text'].append(text)
                        batch['toxicity_scores'].append(example.get('toxicity', 0.0))
                
                return batch
        return {}


class CodeDataLoader(BaseDataLoader):
    """Data loader for Code Generation subsystem"""
    
    def preprocess(self) -> None:
        """Preprocess code data for code generation"""
        logger.info("Preprocessing code data for generation...")
        # Code-specific preprocessing
        # - Syntax validation
        # - Formatting
        # - Tokenization
    
    def get_train_batch(self, indices: Optional[List[int]] = None) -> Dict[str, Any]:
        """Get training batch of code samples"""
        if 'train' not in self.dataset:
            return {}
        
        split = self.dataset['train']
        if indices is None:
            indices = list(range(min(self.batch_size, len(split))))
        
        batch = {
            'code': [],
            'description': [],
        }
        
        for i in indices:
            example = split[i]
            batch['code'].append(example.get('code', example.get('body', '')))
            batch['description'].append(example.get('description', example.get('prompt', '')))
        
        return batch
    
    def get_val_batch(self, indices: Optional[List[int]] = None) -> Dict[str, Any]:
        """Get validation batch"""
        for split_name in ['validation', 'test']:
            if split_name in self.dataset:
                split = self.dataset[split_name]
                if indices is None:
                    indices = list(range(min(self.batch_size, len(split))))
                
                batch = {
                    'code': [],
                    'description': [],
                }
                
                for i in indices:
                    example = split[i]
                    batch['code'].append(example.get('code', example.get('body', '')))
                    batch['description'].append(example.get('description', example.get('prompt', '')))
                
                return batch
        return {}


class QADataLoader(BaseDataLoader):
    """Data loader for Question-Answering subsystem"""
    
    def preprocess(self) -> None:
        """Preprocess QA data"""
        logger.info("Preprocessing question-answering data...")
        # QA-specific preprocessing
        # - Context normalization
        # - Question tokenization
        # - Answer span extraction
    
    def get_train_batch(self, indices: Optional[List[int]] = None) -> Dict[str, Any]:
        """Get training batch of QA samples"""
        if 'train' not in self.dataset:
            return {}
        
        split = self.dataset['train']
        if indices is None:
            indices = list(range(min(self.batch_size, len(split))))
        
        batch = {
            'context': [],
            'question': [],
            'answers': [],
        }
        
        for i in indices:
            example = split[i]
            batch['context'].append(example.get('context', ''))
            batch['question'].append(example.get('question', ''))
            batch['answers'].append(example.get('answers', {}))
        
        return batch
    
    def get_val_batch(self, indices: Optional[List[int]] = None) -> Dict[str, Any]:
        """Get validation batch"""
        for split_name in ['validation', 'test']:
            if split_name in self.dataset:
                split = self.dataset[split_name]
                if indices is None:
                    indices = list(range(min(self.batch_size, len(split))))
                
                batch = {
                    'context': [],
                    'question': [],
                    'answers': [],
                }
                
                for i in indices:
                    example = split[i]
                    batch['context'].append(example.get('context', ''))
                    batch['question'].append(example.get('question', ''))
                    batch['answers'].append(example.get('answers', {}))
                
                return batch
        return {}


# Loader registry
LOADER_REGISTRY: Dict[str, type] = {
    'asr': ASRDataLoader,
    'nlu': NLUDataLoader,
    'safety': SafetyDataLoader,
    'code': CodeDataLoader,
    'qa': QADataLoader,
}


def get_loader(subsystem: str, dataset: DatasetDict, batch_size: int = 32) -> Optional[BaseDataLoader]:
    """Get appropriate data loader for subsystem"""
    loader_class = LOADER_REGISTRY.get(subsystem.lower())
    if loader_class is None:
        logger.warning(f"No loader found for subsystem: {subsystem}")
        return None
    
    return loader_class(dataset, batch_size)


if __name__ == "__main__":
    # Test data loaders
    logging.basicConfig(level=logging.INFO)
    
    print("ASTRA Data Loaders initialized")
    print(f"Available loaders: {list(LOADER_REGISTRY.keys())}")
