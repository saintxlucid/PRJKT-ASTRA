"""Binary provenance tracking system for model evolution."""

import hashlib
from typing import Dict, List, Set, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import logging
import networkx as nx
from collections import defaultdict
import uuid
import subprocess
import sys
import platform
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

@dataclass
class BinaryMetadata:
    """Metadata for a binary artifact."""
    hash: str
    size: int
    timestamp: datetime
    format_version: str
    compiler_info: Dict[str, str]
    build_flags: List[str]
    dependencies: Dict[str, str]  # name -> version

@dataclass
class Operation:
    """Record of an operation performed on a model."""
    op_id: str
    op_type: str
    timestamp: datetime
    parameters: Dict[str, Any]
    input_artifacts: List[str]  # List of artifact hashes
    output_artifacts: List[str]  # List of artifact hashes
    environment: Dict[str, str]
    status: str
    error: Optional[str] = None

@dataclass
class ProvenanceRecord:
    """Complete provenance record for a model."""
    model_id: str
    base_model: str
    creation_time: datetime
    operations: List[Operation]
    current_hash: str
    binary_metadata: Dict[str, BinaryMetadata]
    tags: Dict[str, str]
    ancestry: List[str]  # List of parent model IDs

class ProvenanceTracker:
    """Tracks and manages model binary provenance."""
    
    def __init__(self, storage_path: Path):
        """Initialize the provenance tracker.
        
        Args:
            storage_path: Path for storing provenance data
        """
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._graph = nx.DiGraph()  # Provenance graph
        self._load_existing_records()
        
    def _load_existing_records(self) -> None:
        """Load existing provenance records."""
        for record_file in self.storage_path.glob("*.provenance.json"):
            with open(record_file, 'r') as f:
                data = json.load(f)
                record = self._deserialize_record(data)
                self._add_to_graph(record)
                
    def _add_to_graph(self, record: ProvenanceRecord) -> None:
        """Add a record to the provenance graph."""
        # Add nodes for all artifacts
        for binary_hash, metadata in record.binary_metadata.items():
            self._graph.add_node(
                binary_hash,
                type='artifact',
                metadata=metadata
            )
            
        # Add nodes and edges for operations
        for op in record.operations:
            self._graph.add_node(
                op.op_id,
                type='operation',
                operation=op
            )
            
            # Add edges from inputs to operation
            for input_hash in op.input_artifacts:
                self._graph.add_edge(input_hash, op.op_id)
                
            # Add edges from operation to outputs
            for output_hash in op.output_artifacts:
                self._graph.add_edge(op.op_id, output_hash)
                
    def create_record(self,
                     model_path: Path,
                     base_model: str,
                     tags: Optional[Dict[str, str]] = None) -> ProvenanceRecord:
        """Create a new provenance record.
        
        Args:
            model_path: Path to model file
            base_model: Base model identifier
            tags: Optional metadata tags
            
        Returns:
            New provenance record
        """
        model_id = str(uuid.uuid4())
        binary_hash = self._calculate_file_hash(model_path)
        binary_metadata = self._collect_binary_metadata(model_path)
        
        record = ProvenanceRecord(
            model_id=model_id,
            base_model=base_model,
            creation_time=datetime.now(),
            operations=[],
            current_hash=binary_hash,
            binary_metadata={binary_hash: binary_metadata},
            tags=tags or {},
            ancestry=[base_model]
        )
        
        self._save_record(record)
        self._add_to_graph(record)
        return record
        
    def record_operation(self,
                        record: ProvenanceRecord,
                        op_type: str,
                        parameters: Dict[str, Any],
                        input_paths: List[Path],
                        output_paths: List[Path]) -> ProvenanceRecord:
        """Record an operation in the provenance record.
        
        Args:
            record: Existing provenance record
            op_type: Type of operation performed
            parameters: Operation parameters
            input_paths: Paths to input files
            output_paths: Paths to output files
            
        Returns:
            Updated provenance record
        """
        # Calculate hashes for inputs and outputs
        with ThreadPoolExecutor() as executor:
            input_hashes = list(executor.map(self._calculate_file_hash, input_paths))
            output_hashes = list(executor.map(self._calculate_file_hash, output_paths))
            
        # Collect binary metadata for new artifacts
        for path, hash_value in zip(output_paths, output_hashes):
            if hash_value not in record.binary_metadata:
                record.binary_metadata[hash_value] = self._collect_binary_metadata(path)
                
        # Create operation record
        operation = Operation(
            op_id=str(uuid.uuid4()),
            op_type=op_type,
            timestamp=datetime.now(),
            parameters=parameters,
            input_artifacts=input_hashes,
            output_artifacts=output_hashes,
            environment=self._collect_environment_info(),
            status='completed'
        )
        
        # Update record
        record.operations.append(operation)
        record.current_hash = output_hashes[-1]  # Last output is current state
        
        self._save_record(record)
        self._add_to_graph(record)
        return record
        
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
        
    def _collect_binary_metadata(self, file_path: Path) -> BinaryMetadata:
        """Collect metadata about a binary file."""
        # Get basic file info
        stats = file_path.stat()
        
        # Detect format version (simplified)
        format_version = self._detect_format_version(file_path)
        
        # Get compiler info (simplified)
        compiler_info = {
            'compiler': sys.implementation.name,
            'version': sys.version
        }
        
        # Get build flags (simplified)
        build_flags = [
            f'-O{sys.flags.optimize}',
            f'-{platform.architecture()[0]}'
        ]
        
        # Get dependencies (simplified)
        dependencies = self._collect_dependencies()
        
        return BinaryMetadata(
            hash=self._calculate_file_hash(file_path),
            size=stats.st_size,
            timestamp=datetime.fromtimestamp(stats.st_mtime),
            format_version=format_version,
            compiler_info=compiler_info,
            build_flags=build_flags,
            dependencies=dependencies
        )
        
    def _detect_format_version(self, file_path: Path) -> str:
        """Detect binary format version."""
        # Read first few bytes to detect format
        with open(file_path, 'rb') as f:
            header = f.read(8)
            if header.startswith(b'GGUF'):
                return f"GGUF-{header[4]}.{header[5]}"
            else:
                return "unknown"
                
    def _collect_dependencies(self) -> Dict[str, str]:
        """Collect current Python dependencies."""
        try:
            # Run pip freeze
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'freeze'],
                capture_output=True,
                text=True
            )
            deps = {}
            for line in result.stdout.splitlines():
                if '==' in line:
                    name, version = line.split('==')
                    deps[name] = version
            return deps
        except Exception as e:
            logger.warning(f"Failed to collect dependencies: {e}")
            return {}
            
    def _collect_environment_info(self) -> Dict[str, str]:
        """Collect information about the execution environment."""
        return {
            'python_version': sys.version,
            'platform': platform.platform(),
            'processor': platform.processor(),
            'machine': platform.machine()
        }
        
    def _save_record(self, record: ProvenanceRecord) -> None:
        """Save provenance record to storage."""
        record_path = self.storage_path / f"{record.model_id}.provenance.json"
        with open(record_path, 'w') as f:
            json.dump(self._serialize_record(record), f, indent=2)
            
    def _serialize_record(self, record: ProvenanceRecord) -> Dict[str, Any]:
        """Serialize provenance record to JSON-compatible dict."""
        return {
            'model_id': record.model_id,
            'base_model': record.base_model,
            'creation_time': record.creation_time.isoformat(),
            'operations': [
                {
                    'op_id': op.op_id,
                    'op_type': op.op_type,
                    'timestamp': op.timestamp.isoformat(),
                    'parameters': op.parameters,
                    'input_artifacts': op.input_artifacts,
                    'output_artifacts': op.output_artifacts,
                    'environment': op.environment,
                    'status': op.status,
                    'error': op.error
                }
                for op in record.operations
            ],
            'current_hash': record.current_hash,
            'binary_metadata': {
                h: {
                    'hash': m.hash,
                    'size': m.size,
                    'timestamp': m.timestamp.isoformat(),
                    'format_version': m.format_version,
                    'compiler_info': m.compiler_info,
                    'build_flags': m.build_flags,
                    'dependencies': m.dependencies
                }
                for h, m in record.binary_metadata.items()
            },
            'tags': record.tags,
            'ancestry': record.ancestry
        }
        
    def _deserialize_record(self, data: Dict[str, Any]) -> ProvenanceRecord:
        """Deserialize provenance record from JSON data."""
        return ProvenanceRecord(
            model_id=data['model_id'],
            base_model=data['base_model'],
            creation_time=datetime.fromisoformat(data['creation_time']),
            operations=[
                Operation(
                    op_id=op['op_id'],
                    op_type=op['op_type'],
                    timestamp=datetime.fromisoformat(op['timestamp']),
                    parameters=op['parameters'],
                    input_artifacts=op['input_artifacts'],
                    output_artifacts=op['output_artifacts'],
                    environment=op['environment'],
                    status=op['status'],
                    error=op.get('error')
                )
                for op in data['operations']
            ],
            current_hash=data['current_hash'],
            binary_metadata={
                h: BinaryMetadata(
                    hash=m['hash'],
                    size=m['size'],
                    timestamp=datetime.fromisoformat(m['timestamp']),
                    format_version=m['format_version'],
                    compiler_info=m['compiler_info'],
                    build_flags=m['build_flags'],
                    dependencies=m['dependencies']
                )
                for h, m in data['binary_metadata'].items()
            },
            tags=data['tags'],
            ancestry=data['ancestry']
        )
        
    def query_lineage(self, model_id: str) -> Dict[str, Any]:
        """Query the lineage of a model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Lineage information
        """
        def find_ancestors(node: str) -> Set[str]:
            """Find all ancestors of a node."""
            ancestors = set()
            for pred in self._graph.predecessors(node):
                ancestors.add(pred)
                ancestors.update(find_ancestors(pred))
            return ancestors
            
        def find_descendants(node: str) -> Set[str]:
            """Find all descendants of a node."""
            descendants = set()
            for succ in self._graph.successors(node):
                descendants.add(succ)
                descendants.update(find_descendants(succ))
            return descendants
            
        # Get complete lineage
        ancestors = find_ancestors(model_id)
        descendants = find_descendants(model_id)
        
        # Get operation history
        operations = []
        for node in self._graph.nodes():
            if self._graph.nodes[node].get('type') == 'operation':
                op = self._graph.nodes[node]['operation']
                if op.op_id in ancestors or op.op_id in descendants:
                    operations.append({
                        'id': op.op_id,
                        'type': op.op_type,
                        'timestamp': op.timestamp.isoformat(),
                        'status': op.status
                    })
                    
        return {
            'model_id': model_id,
            'ancestor_count': len(ancestors),
            'descendant_count': len(descendants),
            'operations': sorted(operations, key=lambda x: x['timestamp']),
            'complexity': len(ancestors) + len(descendants)
        }
        
    def verify_integrity(self, model_path: Path) -> Dict[str, Any]:
        """Verify the integrity of a model file.
        
        Args:
            model_path: Path to model file
            
        Returns:
            Verification results
        """
        current_hash = self._calculate_file_hash(model_path)
        
        # Find matching records
        matching_records = []
        for node in self._graph.nodes():
            if (self._graph.nodes[node].get('type') == 'artifact' and
                self._graph.nodes[node]['metadata'].hash == current_hash):
                matching_records.append(node)
                
        if not matching_records:
            return {
                'verified': False,
                'error': 'No matching provenance record found',
                'current_hash': current_hash
            }
            
        # Verify metadata
        current_metadata = self._collect_binary_metadata(model_path)
        stored_metadata = self._graph.nodes[matching_records[0]]['metadata']
        
        return {
            'verified': True,
            'hash_matches': current_hash == stored_metadata.hash,
            'size_matches': current_metadata.size == stored_metadata.size,
            'format_version': current_metadata.format_version,
            'timestamp': current_metadata.timestamp.isoformat(),
            'records_found': len(matching_records)
        }