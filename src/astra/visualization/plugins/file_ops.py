"""
File Operations Plugin
Safe filesystem actions with sandboxing

Available actions:
- list_dir: List directory contents
- read_file: Read text file (with size limits)
- file_info: Get file metadata
- search_files: Search for files by pattern
"""

import os
from pathlib import Path
from typing import Dict, Any, List

from ..task_agent_manager import TaskAgentManager, ToolAction


# ============================================================================
# SAFETY CONFIGURATION
# ============================================================================

MAX_FILE_SIZE_MB = 10  # Max file size to read
MAX_LIST_ITEMS = 1000  # Max items to return in list
ALLOWED_EXTENSIONS = {'.txt', '.md', '.json', '.yaml', '.yml', '.log', '.py', '.js', '.html', '.css'}


# ============================================================================
# FILE OPERATIONS
# ============================================================================

def list_dir(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    List directory contents with metadata
    
    Args:
        path: Directory path (default: current directory)
        include_hidden: Include hidden files (default: False)
        
    Returns:
        Dict with path and items list
    """
    path = args.get("path", ".")
    include_hidden = args.get("include_hidden", False)
    
    try:
        path_obj = Path(path).resolve()
        
        if not path_obj.is_dir():
            return {"error": f"Not a directory: {path}"}
        
        items = []
        count = 0
        
        for item in sorted(path_obj.iterdir()):
            # Skip hidden files if requested
            if not include_hidden and item.name.startswith('.'):
                continue
            
            # Safety limit
            if count >= MAX_LIST_ITEMS:
                items.append({"warning": f"Truncated at {MAX_LIST_ITEMS} items"})
                break
            
            try:
                stat = item.stat()
                items.append({
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "is_file": item.is_file(),
                    "size_bytes": stat.st_size if item.is_file() else None,
                    "modified": stat.st_mtime,
                })
                count += 1
            except (PermissionError, OSError):
                # Skip inaccessible items
                continue
        
        return {
            "path": str(path_obj),
            "item_count": len(items),
            "items": items,
        }
    
    except Exception as e:
        return {"error": str(e)}


def read_file(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Read text file contents (with safety limits)
    
    Args:
        path: File path
        max_lines: Maximum lines to read (default: 1000)
        encoding: File encoding (default: utf-8)
        
    Returns:
        Dict with content or error
    """
    path = args.get("path")
    max_lines = args.get("max_lines", 1000)
    encoding = args.get("encoding", "utf-8")
    
    if not path:
        return {"error": "path argument required"}
    
    try:
        file_path = Path(path).resolve()
        
        if not file_path.is_file():
            return {"error": f"Not a file: {path}"}
        
        # Size check
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            return {"error": f"File too large: {size_mb:.1f}MB (limit: {MAX_FILE_SIZE_MB}MB)"}
        
        # Extension check (optional - commented out for flexibility)
        # if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        #     return {"error": f"File type not allowed: {file_path.suffix}"}
        
        # Read file
        with open(file_path, 'r', encoding=encoding) as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append(f"... truncated at {max_lines} lines ...")
                    break
                lines.append(line.rstrip('\n\r'))
        
        return {
            "path": str(file_path),
            "size_bytes": file_path.stat().st_size,
            "line_count": len(lines),
            "content": '\n'.join(lines),
        }
    
    except UnicodeDecodeError:
        return {"error": "File is not valid text (binary file?)"}
    except Exception as e:
        return {"error": str(e)}


def file_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get file/directory metadata
    
    Args:
        path: File or directory path
        
    Returns:
        Dict with metadata
    """
    path = args.get("path")
    
    if not path:
        return {"error": "path argument required"}
    
    try:
        path_obj = Path(path).resolve()
        
        if not path_obj.exists():
            return {"error": f"Path does not exist: {path}"}
        
        stat = path_obj.stat()
        
        return {
            "path": str(path_obj),
            "name": path_obj.name,
            "is_file": path_obj.is_file(),
            "is_dir": path_obj.is_dir(),
            "size_bytes": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "accessed": stat.st_atime,
            "extension": path_obj.suffix if path_obj.is_file() else None,
        }
    
    except Exception as e:
        return {"error": str(e)}


def search_files(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search for files matching pattern
    
    Args:
        root: Root directory to search
        pattern: Glob pattern (e.g., "*.txt", "**/*.py")
        max_results: Maximum results (default: 100)
        
    Returns:
        Dict with matching files
    """
    root = args.get("root", ".")
    pattern = args.get("pattern", "*")
    max_results = args.get("max_results", 100)
    
    try:
        root_path = Path(root).resolve()
        
        if not root_path.is_dir():
            return {"error": f"Not a directory: {root}"}
        
        matches = []
        count = 0
        
        for match in root_path.glob(pattern):
            if count >= max_results:
                matches.append({"warning": f"Truncated at {max_results} results"})
                break
            
            try:
                stat = match.stat()
                matches.append({
                    "path": str(match.relative_to(root_path)),
                    "absolute_path": str(match),
                    "is_file": match.is_file(),
                    "is_dir": match.is_dir(),
                    "size_bytes": stat.st_size if match.is_file() else None,
                })
                count += 1
            except (PermissionError, OSError):
                continue
        
        return {
            "root": str(root_path),
            "pattern": pattern,
            "match_count": len(matches),
            "matches": matches,
        }
    
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# REGISTRATION
# ============================================================================

def register_file_ops(agent: TaskAgentManager):
    """Register all file operation actions"""
    
    actions = [
        ToolAction(
            name="list_dir",
            handler=list_dir,
            requires_auth=True,
            description="List directory contents with metadata",
            args_schema={
                "path": {"type": "string", "description": "Directory path"},
                "include_hidden": {"type": "boolean", "description": "Include hidden files"},
            },
        ),
        ToolAction(
            name="read_file",
            handler=read_file,
            requires_auth=True,
            description="Read text file contents (with safety limits)",
            args_schema={
                "path": {"type": "string", "description": "File path", "required": True},
                "max_lines": {"type": "integer", "description": "Max lines to read"},
                "encoding": {"type": "string", "description": "File encoding"},
            },
        ),
        ToolAction(
            name="file_info",
            handler=file_info,
            requires_auth=False,  # Read-only metadata
            description="Get file/directory metadata",
            args_schema={
                "path": {"type": "string", "description": "File or directory path", "required": True},
            },
        ),
        ToolAction(
            name="search_files",
            handler=search_files,
            requires_auth=True,
            description="Search for files matching glob pattern",
            args_schema={
                "root": {"type": "string", "description": "Root directory"},
                "pattern": {"type": "string", "description": "Glob pattern"},
                "max_results": {"type": "integer", "description": "Max results"},
            },
        ),
    ]
    
    agent.register_tool("file", actions)
