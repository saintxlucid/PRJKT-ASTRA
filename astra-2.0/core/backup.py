"""
ASTRA Backup and Recovery System
"""
import os
import json
import time
import shutil
import asyncio
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger("astra.backup")

@dataclass
class BackupInfo:
    """Backup metadata"""
    timestamp: str
    version: str
    hash: str
    size: int
    type: str  # core, memory, identity, etc

class BackupManager:
    """ASTRA backup and recovery system"""
    
    def __init__(self, base_path: str = "backups"):
        self.base_path = Path(base_path)
        self.backup_interval = 24 * 60 * 60  # Daily backups
        self.max_backups = 7  # Keep 7 days of backups
        self.backup_types = {
            "core": ["astra_core/"],
            "memory": ["memory/embeddings/", "memory/states/"],
            "identity": ["identity/", "config/"],
            "logs": ["logs/"]
        }
        self._backup_task = None
        
    async def start(self) -> None:
        """Start automated backup system"""
        # Create backup directories
        for backup_type in self.backup_types:
            (self.base_path / backup_type).mkdir(parents=True, exist_ok=True)
            
        # Start backup task
        self._backup_task = asyncio.create_task(
            self._run_backup_schedule()
        )
        
    async def stop(self) -> None:
        """Stop backup system"""
        if self._backup_task:
            self._backup_task.cancel()
            
    async def create_backup(
        self, 
        backup_type: str,
        force: bool = False
    ) -> Optional[BackupInfo]:
        """Create backup of specified type"""
        try:
            if backup_type not in self.backup_types:
                raise ValueError(f"Invalid backup type: {backup_type}")
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            version = "2.0.0"  # TODO: Get from version file
            
            # Create backup directory
            backup_dir = self.base_path / backup_type / timestamp
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy files
            for path in self.backup_types[backup_type]:
                src = Path(path)
                if not src.exists():
                    logger.warning(f"Source path does not exist: {path}")
                    continue
                    
                dst = backup_dir / src.name
                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                    
            # Calculate hash
            hash_value = await self._hash_directory(backup_dir)
            
            # Get size
            size = sum(f.stat().st_size for f in backup_dir.rglob("*") if f.is_file())
            
            # Create metadata
            info = BackupInfo(
                timestamp=timestamp,
                version=version,
                hash=hash_value,
                size=size,
                type=backup_type
            )
            
            # Save metadata
            meta_file = backup_dir / "backup.json"
            meta_file.write_text(json.dumps(dataclass.asdict(info)))
            
            await self._cleanup_old_backups(backup_type)
            
            logger.info(f"Created {backup_type} backup: {timestamp}")
            return info
            
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            return None
            
    async def restore_backup(
        self,
        backup_type: str,
        timestamp: Optional[str] = None
    ) -> bool:
        """Restore from backup"""
        try:
            if backup_type not in self.backup_types:
                raise ValueError(f"Invalid backup type: {backup_type}")
                
            # Find latest backup if timestamp not specified
            backup_dir = self.base_path / backup_type
            if not timestamp:
                backups = sorted(backup_dir.iterdir(), key=lambda p: p.name)
                if not backups:
                    raise FileNotFoundError("No backups found")
                backup_path = backups[-1]
            else:
                backup_path = backup_dir / timestamp
                if not backup_path.exists():
                    raise FileNotFoundError(f"Backup not found: {timestamp}")
                    
            # Verify hash
            meta_file = backup_path / "backup.json"
            if meta_file.exists():
                meta = json.loads(meta_file.read_text())
                stored_hash = meta["hash"]
                current_hash = await self._hash_directory(backup_path)
                if stored_hash != current_hash:
                    raise ValueError("Backup corruption detected")
                    
            # Restore files
            for path in self.backup_types[backup_type]:
                src = backup_path / Path(path).name
                if not src.exists():
                    logger.warning(f"Backup file missing: {src}")
                    continue
                    
                dst = Path(path)
                if dst.exists():
                    if dst.is_dir():
                        shutil.rmtree(dst)
                    else:
                        dst.unlink()
                        
                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                    
            logger.info(f"Restored {backup_type} from: {backup_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            return False
            
    async def _run_backup_schedule(self) -> None:
        """Run automated backup schedule"""
        while True:
            for backup_type in self.backup_types:
                await self.create_backup(backup_type)
            await asyncio.sleep(self.backup_interval)
            
    async def _cleanup_old_backups(self, backup_type: str) -> None:
        """Remove old backups beyond retention limit"""
        backup_dir = self.base_path / backup_type
        backups = sorted(backup_dir.iterdir(), key=lambda p: p.name)
        
        while len(backups) > self.max_backups:
            old_backup = backups.pop(0)
            if old_backup.is_dir():
                shutil.rmtree(old_backup)
            logger.info(f"Removed old backup: {old_backup.name}")
            
    async def _hash_directory(self, path: Path) -> str:
        """Calculate hash of directory contents"""
        sha256 = hashlib.sha256()
        
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file():
                # Skip metadata file in hash calculation
                if file_path.name == "backup.json":
                    continue
                    
                sha256.update(file_path.read_bytes())
                
        return sha256.hexdigest()

_instance = None

def get_backup_manager() -> BackupManager:
    """Get backup manager singleton"""
    global _instance
    if _instance is None:
        _instance = BackupManager()
    return _instance