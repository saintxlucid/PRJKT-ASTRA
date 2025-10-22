# provenance.py
from __future__ import annotations
from pathlib import Path
import hashlib, hmac, json, time, os
from .gguf_io import GGUFIO

SECRET = os.environ.get("ASTRA_OPERATOR_SECRET", "dev-change-me")

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()
    """Handles model signing and provenance."""
    
def sign_file(path: str, meta: dict) -> dict:
    checksum = sha256_file(path)
    sig = hmac.new(SECRET.encode(), checksum.encode(), hashlib.sha256).hexdigest()
    io = GGUFIO(path)
    io.kv_set("astra.checksum", checksum)
    io.kv_set("astra.signature", sig)
    io.kv_set("astra.meta", meta)
    io.kv_set("astra.builtAt", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    io.save_kv()
    return {"checksum": checksum, "signature": sig}
def verify_signature(path: str) -> bool:
    io = GGUFIO(path)
    checksum = io.kv_get("astra.checksum")
    signature = io.kv_get("astra.signature")
    if not checksum or not signature:
        return False
    expected = hmac.new(SECRET.encode(), checksum.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
        
    def embed_provenance(
        self,
        model_path: Path,
        snapshot_id: str,
        adapter_info: Dict
    ) -> None:
        """Embed provenance metadata in model."""
        gguf = GGUFFile(model_path)
        
        # Compute signatures
        checksum, signature = self.sign_model(model_path)
        
        # Prepare provenance data
        provenance = {
            'astra.version': '1.1.0',
            'astra.checksum': checksum,
            'astra.signature': signature,
            'astra.snapshot_id': snapshot_id,
            'astra.built_at': datetime.now().isoformat(),
            'astra.adapters': json.dumps(adapter_info),
            'astra.ops': 'merge,quantize,validate'
        }
        
        # Write provenance KV pairs
        for key, value in provenance.items():
            gguf.write_kv(key, value)
            
    def commit_model(self, model_path: Path) -> Path:
        """Commit model with atomic rename."""
        model_path = Path(model_path)
        temp_path = model_path.with_suffix('.tmp')
        final_path = model_path
        
        if not self.verify_signature(temp_path):
            raise ValueError("Model signature verification failed")
            
        # Atomic rename
        import os
        if hasattr(os, 'replace'):
            os.replace(temp_path, final_path)  # Atomic on Unix and Windows
        else:
            import shutil
            shutil.move(temp_path, final_path)
            
        return final_path
        
    def rollback_model(self, model_path: Path) -> None:
        """Rollback to backup version."""
        model_path = Path(model_path)
        backup_path = model_path.with_suffix('.backup')
        
        if not backup_path.exists():
            raise FileNotFoundError(f"No backup found at {backup_path}")
            
        # Verify backup signature
        if not self.verify_signature(backup_path):
            raise ValueError("Backup signature verification failed")
            
        # Atomic restore
        import os
        if hasattr(os, 'replace'):
            os.replace(backup_path, model_path)
        else:
            import shutil
            shutil.move(backup_path, model_path)