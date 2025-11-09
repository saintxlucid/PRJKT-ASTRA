import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional

class SignatureVerifier:
    """Verifies GGUF file signatures and handles rollbacks if needed."""
    
    def __init__(self, model_path: Path):
        self.model_path = Path(model_path)
        self.backup_path = self.model_path.with_suffix('.backup')
        
    def compute_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
        
    def verify_signature(self) -> bool:
        """Verify model file signature matches manifest."""
        manifest_path = self.model_path.parent / 'manifest.json'
        if not manifest_path.exists():
            raise ValueError(f"No manifest found at {manifest_path}")
            
        with open(manifest_path) as f:
            manifest = json.load(f)
            
        expected_hash = manifest['evolved_model']['checksum'].split(':')[1]
        actual_hash = self.compute_hash(self.model_path)
        
        return expected_hash == actual_hash
        
    def backup_model(self) -> None:
        """Create backup of current model file."""
        import shutil
        shutil.copy2(self.model_path, self.backup_path)
        
    def restore_backup(self) -> None:
        """Restore model from backup file."""
        if not self.backup_path.exists():
            raise FileNotFoundError(f"No backup found at {self.backup_path}")
            
        import shutil
        shutil.move(self.backup_path, self.model_path)
        
    def suggest_rollback(self) -> Dict[str, Any]:
        """Generate rollback suggestion if signature verification fails."""
        return {
            'action': 'rollback',
            'reason': 'Signature verification failed - possible file tampering',
            'backup_path': str(self.backup_path),
            'command': f'gguf-commit --rollback {self.model_path}'
        }
        
    def verify_and_protect(self) -> Dict[str, Any]:
        """Main verification workflow with rollback handling."""
        try:
            # Create backup before verification
            self.backup_model()
            
            # Verify signature
            if self.verify_signature():
                return {
                    'status': 'verified',
                    'message': 'Model signature verified successfully'
                }
            
            # Signature mismatch - suggest rollback
            return self.suggest_rollback()
            
        except Exception as e:
            # Handle verification errors
            return {
                'status': 'error',
                'message': str(e),
                'suggestion': self.suggest_rollback()
            }