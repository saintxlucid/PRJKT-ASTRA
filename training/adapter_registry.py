"""
Adapter registry for safety and governance
"""
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import hmac
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class AdapterMetadata:
    """Metadata for a registered adapter"""
    adapter_id: str
    name: str
    version: str
    base_model: str
    created_at: datetime
    hash: str
    signature: str
    eval_metrics: Dict[str, float]
    tags: List[str]
    status: str

@dataclass
class RegistryEntry:
    """Full registry entry with security info"""
    metadata: AdapterMetadata
    allowed_users: Set[str]
    allowed_contexts: Set[str]
    usage_policy: Dict[str, Any]
    audit_log: List[Dict[str, Any]]

class AdapterRegistry:
    """Manages adapter registration and access control"""
    
    def __init__(
        self,
        registry_path: str,
        signing_key: str,
        require_signing: bool = True
    ):
        self.registry_path = Path(registry_path)
        self.signing_key = signing_key.encode()
        self.require_signing = require_signing
        self.registry: Dict[str, RegistryEntry] = {}
        
        # Load existing registry
        self._load_registry()
        
    def register_adapter(
        self,
        adapter_path: str,
        name: str,
        version: str,
        base_model: str,
        eval_metrics: Dict[str, float],
        tags: List[str],
        allowed_users: Optional[Set[str]] = None,
        allowed_contexts: Optional[Set[str]] = None,
        usage_policy: Optional[Dict[str, Any]] = None
    ) -> AdapterMetadata:
        """
        Register a new adapter
        
        Args:
            adapter_path: Path to adapter files
            name: Adapter name
            version: Version string
            base_model: Base model name
            eval_metrics: Evaluation metrics
            tags: Categorization tags
            allowed_users: Users with access
            allowed_contexts: Allowed usage contexts
            usage_policy: Usage restrictions
            
        Returns:
            Adapter metadata
        """
        # Generate adapter ID
        adapter_id = self._generate_id(name, version)
        
        # Compute hash
        adapter_hash = self._hash_adapter(adapter_path)
        
        # Sign adapter
        signature = self._sign_adapter(
            adapter_id,
            adapter_hash,
            eval_metrics
        )
        
        # Create metadata
        metadata = AdapterMetadata(
            adapter_id=adapter_id,
            name=name,
            version=version,
            base_model=base_model,
            created_at=datetime.utcnow(),
            hash=adapter_hash,
            signature=signature,
            eval_metrics=eval_metrics,
            tags=tags,
            status="active"
        )
        
        # Create registry entry
        entry = RegistryEntry(
            metadata=metadata,
            allowed_users=allowed_users or set(),
            allowed_contexts=allowed_contexts or set(),
            usage_policy=usage_policy or {},
            audit_log=[]
        )
        
        self.registry[adapter_id] = entry
        
        # Save registry
        self._save_registry()
        
        return metadata
        
    def get_adapter(
        self,
        adapter_id: str,
        user: str,
        context: str
    ) -> Optional[AdapterMetadata]:
        """
        Get adapter if user has access
        
        Args:
            adapter_id: Adapter identifier
            user: User requesting access
            context: Usage context
            
        Returns:
            Adapter metadata if access allowed
        """
        if adapter_id not in self.registry:
            return None
            
        entry = self.registry[adapter_id]
        
        # Check access
        if not self._check_access(entry, user, context):
            return None
            
        # Verify signature if required
        if self.require_signing:
            if not self._verify_signature(entry.metadata):
                return None
                
        # Log access
        self._log_access(entry, user, context)
        
        return entry.metadata
        
    def list_adapters(
        self,
        user: str,
        tag_filter: Optional[List[str]] = None
    ) -> List[AdapterMetadata]:
        """List adapters available to user"""
        accessible = []
        
        for entry in self.registry.values():
            if not entry.allowed_users or user in entry.allowed_users:
                if not tag_filter or any(
                    tag in entry.metadata.tags
                    for tag in tag_filter
                ):
                    accessible.append(entry.metadata)
                    
        return accessible
        
    def deactivate_adapter(self, adapter_id: str) -> None:
        """Deactivate adapter"""
        if adapter_id in self.registry:
            self.registry[adapter_id].metadata.status = "inactive"
            self._save_registry()
            
    def _generate_id(self, name: str, version: str) -> str:
        """Generate stable adapter ID"""
        content = f"{name}_{version}"
        hasher = hashlib.sha256()
        hasher.update(content.encode())
        return hasher.hexdigest()[:16]
        
    def _hash_adapter(self, adapter_path: str) -> str:
        """Compute hash of adapter files"""
        hasher = hashlib.sha256()
        
        adapter_dir = Path(adapter_path)
        for f in sorted(adapter_dir.glob("**/*")):
            if f.is_file():
                hasher.update(f.read_bytes())
                
        return hasher.hexdigest()
        
    def _sign_adapter(
        self,
        adapter_id: str,
        adapter_hash: str,
        eval_metrics: Dict[str, float]
    ) -> str:
        """Create HMAC signature"""
        # Create signing string
        content = f"{adapter_id}:{adapter_hash}"
        
        # Add sorted metrics
        metrics_str = ":".join(
            f"{k}={v}"
            for k, v in sorted(eval_metrics.items())
        )
        content = f"{content}:{metrics_str}"
        
        # Generate HMAC
        signer = hmac.new(
            self.signing_key,
            content.encode(),
            hashlib.sha256
        )
        return signer.hexdigest()
        
    def _verify_signature(self, metadata: AdapterMetadata) -> bool:
        """Verify adapter signature"""
        expected = self._sign_adapter(
            metadata.adapter_id,
            metadata.hash,
            metadata.eval_metrics
        )
        return hmac.compare_digest(
            metadata.signature.encode(),
            expected.encode()
        )
        
    def _check_access(
        self,
        entry: RegistryEntry,
        user: str,
        context: str
    ) -> bool:
        """Check if user has access"""
        if entry.metadata.status != "active":
            return False
            
        if entry.allowed_users and user not in entry.allowed_users:
            return False
            
        if entry.allowed_contexts and context not in entry.allowed_contexts:
            return False
            
        return True
        
    def _log_access(
        self,
        entry: RegistryEntry,
        user: str,
        context: str
    ) -> None:
        """Log adapter access"""
        entry.audit_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "user": user,
            "context": context,
            "adapter_id": entry.metadata.adapter_id
        })
        
    def _load_registry(self) -> None:
        """Load registry from disk"""
        if not self.registry_path.exists():
            return
            
        try:
            with open(self.registry_path) as f:
                data = json.load(f)
                
            for entry in data["entries"]:
                metadata = AdapterMetadata(
                    adapter_id=entry["metadata"]["adapter_id"],
                    name=entry["metadata"]["name"],
                    version=entry["metadata"]["version"],
                    base_model=entry["metadata"]["base_model"],
                    created_at=datetime.fromisoformat(
                        entry["metadata"]["created_at"]
                    ),
                    hash=entry["metadata"]["hash"],
                    signature=entry["metadata"]["signature"],
                    eval_metrics=entry["metadata"]["eval_metrics"],
                    tags=entry["metadata"]["tags"],
                    status=entry["metadata"]["status"]
                )
                
                registry_entry = RegistryEntry(
                    metadata=metadata,
                    allowed_users=set(entry["allowed_users"]),
                    allowed_contexts=set(entry["allowed_contexts"]),
                    usage_policy=entry["usage_policy"],
                    audit_log=entry["audit_log"]
                )
                
                self.registry[metadata.adapter_id] = registry_entry
                
        except Exception as e:
            logger.error(
                "Error loading registry",
                exc_info=True
            )
            
    def _save_registry(self) -> None:
        """Save registry to disk"""
        try:
            data = {
                "entries": [
                    {
                        "metadata": {
                            "adapter_id": e.metadata.adapter_id,
                            "name": e.metadata.name,
                            "version": e.metadata.version,
                            "base_model": e.metadata.base_model,
                            "created_at": e.metadata.created_at.isoformat(),
                            "hash": e.metadata.hash,
                            "signature": e.metadata.signature,
                            "eval_metrics": e.metadata.eval_metrics,
                            "tags": e.metadata.tags,
                            "status": e.metadata.status
                        },
                        "allowed_users": list(e.allowed_users),
                        "allowed_contexts": list(e.allowed_contexts),
                        "usage_policy": e.usage_policy,
                        "audit_log": e.audit_log
                    }
                    for e in self.registry.values()
                ]
            }
            
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(
                "Error saving registry",
                exc_info=True
            )