"""
ASTRA Filesystem Tools
Safe file operations with automatic backup support.
Created: October 16, 2025
"""
from pathlib import Path
import shutil
import zipfile
import asyncio
from datetime import datetime
import structlog
from typing import Optional, List

from src.astra.core.tool_bus import tool

logger = structlog.get_logger()

def create_backup_name(path: Path) -> str:
    """Create a backup filename with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{path.stem}_{timestamp}_backup{path.suffix}"

async def create_backup(path: Path) -> Path:
    """
    Create a backup of a file or directory.
    Args:
        path: Path to backup
    Returns:
        Path to backup file
    """
    path = Path(path).resolve()
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    
    backup_path = backup_dir / create_backup_name(path)
    
    if path.is_dir():
        # Create zip archive for directories
        with zipfile.ZipFile(backup_path.with_suffix('.zip'), 'w') as zf:
            for file in path.rglob('*'):
                if file.is_file():
                    zf.write(file, file.relative_to(path))
        backup_path = backup_path.with_suffix('.zip')
    else:
        # Simple file copy
        shutil.copy2(path, backup_path)
        
    logger.info(
        "Created backup",
        original=str(path),
        backup=str(backup_path)
    )
    return backup_path

@tool(
    name="file_read",
    description="Read a file safely",
    schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "binary": {"type": "boolean", "default": False}
        },
        "required": ["path"]
    },
    timeout=30
)
async def read_file(path: str, binary: bool = False) -> str:
    """Read a file with timeout"""
    path = Path(path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
        
    mode = 'rb' if binary else 'r'
    async with asyncio.Lock():  # Prevent concurrent access
        with open(path, mode) as f:
            return f.read()

@tool(
    name="file_write",
    description="Write to a file safely with backup",
    schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
            "binary": {"type": "boolean", "default": False}
        },
        "required": ["path", "content"]
    },
    timeout=30
)
async def write_file(path: str, content: str, binary: bool = False) -> dict:
    """Write to a file with backup"""
    path = Path(path).resolve()
    
    # Create backup if file exists
    backup_path = None
    if path.exists():
        backup_path = await create_backup(path)
    
    mode = 'wb' if binary else 'w'
    async with asyncio.Lock():
        with open(path, mode) as f:
            f.write(content)
            
    return {
        "path": str(path),
        "backup": str(backup_path) if backup_path else None
    }

@tool(
    name="file_delete",
    description="Delete a file/directory with mandatory backup",
    schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"}
        },
        "required": ["path"]
    },
    timeout=60
)
async def delete_file(path: str) -> dict:
    """Delete a file/directory with mandatory backup"""
    path = Path(path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")
        
    # Always create backup before deletion
    backup_path = await create_backup(path)
    
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
        
    return {
        "deleted": str(path),
        "backup": str(backup_path)
    }

@tool(
    name="file_move",
    description="Move/rename a file/directory with backup",
    schema={
        "type": "object",
        "properties": {
            "source": {"type": "string"},
            "destination": {"type": "string"}
        },
        "required": ["source", "destination"]
    },
    timeout=60
)
async def move_file(source: str, destination: str) -> dict:
    """Move/rename a file with backup"""
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    
    if not source.exists():
        raise FileNotFoundError(f"Source not found: {source}")
        
    # Create backup of source
    backup_path = await create_backup(source)
    
    # Move the file
    shutil.move(str(source), str(destination))
    
    return {
        "source": str(source),
        "destination": str(destination),
        "backup": str(backup_path)
    }

@tool(
    name="file_restore",
    description="Restore a file from backup",
    schema={
        "type": "object",
        "properties": {
            "backup_path": {"type": "string"},
            "restore_path": {"type": "string", "optional": True}
        },
        "required": ["backup_path"]
    },
    timeout=60
)
async def restore_backup(backup_path: str, restore_path: Optional[str] = None) -> dict:
    """
    Restore a file from backup.
    Args:
        backup_path: Path to backup file
        restore_path: Optional custom restore location
    """
    backup_path = Path(backup_path).resolve()
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")
    
    if restore_path:
        restore_path = Path(restore_path).resolve()
    else:
        # Extract original path from backup name
        original_name = '_'.join(backup_path.stem.split('_')[:-2])
        restore_path = backup_path.parent / f"{original_name}{backup_path.suffix}"
    
    if backup_path.suffix == '.zip':
        # Restore directory from zip
        with zipfile.ZipFile(backup_path, 'r') as zf:
            zf.extractall(restore_path)
    else:
        # Restore single file
        shutil.copy2(backup_path, restore_path)
        
    return {
        "backup": str(backup_path),
        "restored_to": str(restore_path)
    }

@tool(
    name="list_backups",
    description="List available backups",
    schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "optional": True}
        }
    },
    timeout=30
)
async def list_backups(path: Optional[str] = None) -> List[dict]:
    """
    List available backups.
    Args:
        path: Optional path to filter backups for
    Returns:
        List of backup details
    """
    backup_dir = Path("backups")
    if not backup_dir.exists():
        return []
        
    backups = []
    for backup in backup_dir.glob("*_backup*"):
        if path:
            # Filter for specific path
            original_name = '_'.join(backup.stem.split('_')[:-2])
            if original_name not in Path(path).name:
                continue
                
        backups.append({
            "backup_path": str(backup),
            "timestamp": datetime.strptime(
                backup.stem.split('_')[-2],
                "%Y%m%d_%H%M%S"
            ).isoformat(),
            "size": backup.stat().st_size
        })
        
    return sorted(backups, key=lambda x: x["timestamp"], reverse=True)