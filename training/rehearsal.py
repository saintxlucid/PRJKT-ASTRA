"""
Experience replay and rehearsal for safe continual learning
"""
from typing import List, Dict, Any, Optional, Iterator
from dataclasses import dataclass
import random
from datetime import datetime
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

@dataclass
class ExperienceExample:
    """Training example with metadata"""
    query: str
    response: str
    score: float
    timestamp: datetime
    tags: List[str]
    metadata: Dict[str, Any]

class ExperienceBuffer:
    """Stores and samples training examples"""
    
    def __init__(
        self,
        max_size: int = 10000,
        min_score: float = 0.7,
        storage_path: Optional[str] = None
    ):
        self.max_size = max_size
        self.min_score = min_score
        self.storage_path = storage_path
        self.examples: List[ExperienceExample] = []
        
    def add_example(
        self,
        example: ExperienceExample
    ) -> bool:
        """
        Add example to buffer if it meets criteria
        Returns True if example was added
        """
        if example.score < self.min_score:
            return False
            
        self.examples.append(example)
        
        # Trim buffer if needed
        if len(self.examples) > self.max_size:
            # Remove oldest examples
            excess = len(self.examples) - self.max_size
            self.examples = self.examples[excess:]
            
        if self.storage_path:
            self._save_example(example)
            
        return True
        
    def sample_batch(
        self,
        batch_size: int,
        tag_filter: Optional[List[str]] = None
    ) -> List[ExperienceExample]:
        """Sample a random batch of examples"""
        pool = self.examples
        if tag_filter:
            pool = [
                ex for ex in pool
                if any(tag in ex.tags for tag in tag_filter)
            ]
            
        if not pool:
            return []
            
        return random.sample(
            pool,
            min(batch_size, len(pool))
        )
        
    def _save_example(self, example: ExperienceExample):
        """Save example to disk"""
        if not self.storage_path:
            return
            
        storage_dir = Path(self.storage_path)
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as JSON
        data = {
            "query": example.query,
            "response": example.response,
            "score": example.score,
            "timestamp": example.timestamp.isoformat(),
            "tags": example.tags,
            "metadata": example.metadata
        }
        
        # Use timestamp as filename
        filename = example.timestamp.strftime("%Y%m%d_%H%M%S.json")
        with open(storage_dir / filename, 'w') as f:
            json.dump(data, f, indent=2)
            
    def load_from_disk(self) -> int:
        """Load saved examples from disk"""
        if not self.storage_path:
            return 0
            
        storage_dir = Path(self.storage_path)
        if not storage_dir.exists():
            return 0
            
        loaded = 0
        for f in storage_dir.glob("*.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                    
                example = ExperienceExample(
                    query=data["query"],
                    response=data["response"], 
                    score=data["score"],
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    tags=data["tags"],
                    metadata=data["metadata"]
                )
                
                if self.add_example(example):
                    loaded += 1
                    
            except Exception as e:
                logger.error(
                    f"Error loading example from {f}",
                    exc_info=True
                )
                
        return loaded

class RehearsalDataset(Dataset):
    """PyTorch dataset for experience replay"""
    
    def __init__(
        self,
        buffer: ExperienceBuffer,
        tokenizer: Any,
        max_length: int = 512
    ):
        self.buffer = buffer
        self.tokenizer = tokenizer
        self.max_length = max_length
        
    def __len__(self) -> int:
        return len(self.buffer.examples)
        
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        example = self.buffer.examples[idx]
        
        # Format as instruction
        text = f"""Question: {example.query}
        Answer: {example.response}"""
        
        # Tokenize
        tokens = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )
        
        return {
            "input_ids": tokens["input_ids"].squeeze(),
            "attention_mask": tokens["attention_mask"].squeeze(),
            "score": torch.tensor(example.score)
        }

def create_rehearsal_loader(
    buffer: ExperienceBuffer,
    tokenizer: Any,
    batch_size: int = 8,
    max_length: int = 512,
    shuffle: bool = True
) -> DataLoader:
    """Create DataLoader for rehearsal"""
    dataset = RehearsalDataset(
        buffer,
        tokenizer,
        max_length
    )
    
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle
    )