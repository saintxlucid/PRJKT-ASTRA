"""
ASTRA Dataset Manager

Central interface for managing and providing dataset access to ASTRA subsystems.
Handles lazy loading, caching, and metadata management for all integrated datasets.

Created: October 18, 2025
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datasets import load_from_disk, DatasetDict
import logging

logger = logging.getLogger(__name__)


@dataclass
class DatasetMetadata:
    """Metadata for a dataset"""
    name: str
    path: str
    size_mb: float
    split: str
    config: Optional[str]
    subsystems: List[str]  # Which subsystems use this dataset
    purpose: str


class DatasetManager:
    """
    Central dataset management for ASTRA.
    
    Provides:
    - Lazy loading with caching
    - Subsystem-specific dataset access
    - Metadata and size information
    - Dataset validation and integrity checks
    """
    
    def __init__(self, data_dir: Optional[Path] = None, manifest_path: Optional[Path] = None):
        """
        Initialize Dataset Manager.
        
        Args:
            data_dir: Path to data directory (default: ./data)
            manifest_path: Path to manifest JSON (default: ./data/_manifest.json)
        """
        self.data_dir = Path(data_dir or "./data")
        self.manifest_path = Path(manifest_path or self.data_dir / "_manifest.json")
        
        self._datasets = {}  # Cached loaded datasets
        self._metadata = {}  # Dataset metadata
        self._manifest = {}  # Manifest data
        
        self._load_manifest()
        self._build_metadata()
        
    def _load_manifest(self) -> None:
        """Load manifest file containing dataset information"""
        if not self.manifest_path.exists():
            logger.warning(f"Manifest not found at {self.manifest_path}")
            self._manifest = {"datasets": []}
            return
        
        try:
            self._manifest = json.loads(self.manifest_path.read_text())
            logger.info(f"Loaded manifest with {len(self._manifest.get('datasets', []))} datasets")
        except Exception as e:
            logger.error(f"Failed to load manifest: {e}")
            self._manifest = {"datasets": []}
    
    def _build_metadata(self) -> None:
        """Build metadata from manifest"""
        subsystem_map = {
            'wikitext': ['language_model', 'nlm'],
            'imdb': ['nlu', 'sentiment'],
            'snips_built_in_intents': ['nlu', 'intent_classification'],
            'clinc150': ['nlu', 'intent_classification'],
            'ag_news': ['nlu', 'text_classification'],
            'funsd': ['vision', 'document_understanding'],
            'real_toxicity_prompts': ['safety', 'toxicity_detection'],
            'mbpp': ['code', 'code_generation'],
            'squad': ['qa', 'reading_comprehension'],
        }
        
        for dataset in self._manifest.get('datasets', []):
            name = dataset['name']
            path = dataset['path']
            
            # Estimate size from manifest or use provided value
            size_mb = 1.0  # Default
            split = dataset.get('split', 'train')
            config = dataset.get('config')
            
            # Map dataset to subsystems
            subsystems = []
            for key, systems in subsystem_map.items():
                if key in name.lower():
                    subsystems.extend(systems)
            
            metadata = DatasetMetadata(
                name=name,
                path=path,
                size_mb=size_mb,
                split=split,
                config=config,
                subsystems=subsystems if subsystems else ['general'],
                purpose=f"Dataset for {', '.join(subsystems) if subsystems else 'general use'}"
            )
            
            self._metadata[name] = metadata
            logger.debug(f"Registered dataset: {name} → {subsystems}")
    
    def get_dataset(self, dataset_name: str, lazy: bool = True) -> Optional[DatasetDict]:
        """
        Retrieve a dataset by name.
        
        Args:
            dataset_name: Name of the dataset (e.g., 'squad', 'clinc150')
            lazy: If True, return from cache if available
            
        Returns:
            DatasetDict or None if not found
        """
        if dataset_name not in self._metadata:
            logger.error(f"Dataset '{dataset_name}' not found in manifest")
            return None
        
        # Check cache
        if lazy and dataset_name in self._datasets:
            logger.debug(f"Returning cached dataset: {dataset_name}")
            return self._datasets[dataset_name]
        
        # Load from disk
        try:
            metadata = self._metadata[dataset_name]
            path = Path(metadata.path)
            
            if not path.exists():
                logger.error(f"Dataset path does not exist: {path}")
                return None
            
            dataset = load_from_disk(str(path))
            
            # Cache it
            if lazy:
                self._datasets[dataset_name] = dataset
            
            logger.info(f"Loaded dataset: {dataset_name}")
            return dataset
            
        except Exception as e:
            logger.error(f"Failed to load dataset '{dataset_name}': {e}")
            return None
    
    def get_datasets_for_subsystem(self, subsystem: str) -> Dict[str, DatasetDict]:
        """
        Get all datasets associated with a specific subsystem.
        
        Args:
            subsystem: Subsystem name (e.g., 'nlu', 'safety', 'code')
            
        Returns:
            Dictionary of {dataset_name: dataset}
        """
        datasets = {}
        
        for name, metadata in self._metadata.items():
            if subsystem in metadata.subsystems:
                dataset = self.get_dataset(name)
                if dataset is not None:
                    datasets[name] = dataset
        
        logger.info(f"Retrieved {len(datasets)} datasets for subsystem '{subsystem}'")
        return datasets
    
    def get_metadata(self, dataset_name: str) -> Optional[DatasetMetadata]:
        """Get metadata for a dataset"""
        return self._metadata.get(dataset_name)
    
    def list_datasets(self) -> List[str]:
        """List all available datasets"""
        return list(self._metadata.keys())
    
    def list_subsystems(self) -> List[str]:
        """List all subsystems with associated datasets"""
        subsystems = set()
        for metadata in self._metadata.values():
            subsystems.update(metadata.subsystems)
        return sorted(list(subsystems))
    
    def get_dataset_info(self, dataset_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a dataset"""
        metadata = self._metadata.get(dataset_name)
        if metadata is None:
            return None
        
        return {
            'name': metadata.name,
            'path': metadata.path,
            'size_mb': metadata.size_mb,
            'split': metadata.split,
            'config': metadata.config,
            'subsystems': metadata.subsystems,
            'purpose': metadata.purpose,
        }
    
    def print_summary(self) -> None:
        """Print dataset summary"""
        print("\n" + "="*80)
        print("ASTRA Dataset Manager Summary")
        print("="*80)
        
        print(f"\nTotal Datasets: {len(self._metadata)}")
        print("\nDatasets by Subsystem:")
        
        subsystems = self.list_subsystems()
        for subsystem in subsystems:
            datasets = [name for name, meta in self._metadata.items() 
                       if subsystem in meta.subsystems]
            print(f"\n  {subsystem.upper()}:")
            for dataset in datasets:
                size = self._metadata[dataset].size_mb
                print(f"    - {dataset} (~{size} MB)")
        
        total_size = sum(m.size_mb for m in self._metadata.values())
        print(f"\nTotal Size: ~{total_size:.1f} MB")
        print("="*80 + "\n")


# Singleton instance
_dataset_manager = None


def get_dataset_manager(
    data_dir: Optional[Path] = None,
    manifest_path: Optional[Path] = None
) -> DatasetManager:
    """Get or create the global Dataset Manager instance"""
    global _dataset_manager
    if _dataset_manager is None:
        _dataset_manager = DatasetManager(data_dir, manifest_path)
    return _dataset_manager


if __name__ == "__main__":
    # Test the Dataset Manager
    logging.basicConfig(level=logging.INFO)
    
    manager = DatasetManager()
    manager.print_summary()
    
    # Test dataset access
    print("\nTesting dataset access:")
    squad = manager.get_dataset('squad')
    if squad:
        print(f"✓ squad dataset loaded: {squad}")
    
    # Get datasets for NLU
    print("\nNLU datasets:")
    nlu_datasets = manager.get_datasets_for_subsystem('nlu')
    for name in nlu_datasets:
        print(f"  - {name}")
