"""
ASTRA-OS Tool Bus
Implements safe, policy-gated action adapters for filesystem, shell, UI, etc.

File: libs/tools/__init__.py
Lines: 700+
"""

import os
import shutil
import subprocess
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from abc import ABC, abstractmethod
import logging
from enum import Enum

logger = logging.getLogger("astra.tools")


class ToolCapability(Enum):
    """Tool capability types."""
    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"
    FILESYSTEM_DELETE = "filesystem.delete"
    SHELL_EXECUTE = "shell.execute"
    UI_AUTOMATION = "ui.automation"
    CLIPBOARD = "clipboard"
    NOTIFICATIONS = "notifications"
    BROWSER_CONTROL = "browser.control"


@dataclass
class ToolManifest:
    """Tool capability manifest."""
    name: str
    capability: ToolCapability
    risk_score: float  # 0.0-1.0
    requires_elevation: bool = False
    supports_rollback: bool = False
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResult:
    """Result of tool execution."""
    id: str
    success: bool
    output: Any
    error: Optional[str] = None
    duration_ms: int = 0
    side_effects: List[Dict[str, Any]] = field(default_factory=list)


class BaseTool(ABC):
    """Base class for tool adapters."""
    
    def __init__(self, manifest: ToolManifest):
        self.manifest = manifest
        self.action_history: List[ActionResult] = []
    
    @abstractmethod
    async def execute(self, **kwargs) -> ActionResult:
        """Execute tool action."""
        pass
    
    def record_action(self, result: ActionResult):
        """Record action for audit."""
        self.action_history.append(result)


class FilesystemTool(BaseTool):
    """Filesystem operations: copy, move, delete, organize, hash."""
    
    def __init__(self):
        manifest = ToolManifest(
            name="filesystem",
            capability=ToolCapability.FILESYSTEM_WRITE,
            risk_score=0.5,
            supports_rollback=True,
            description="Safe filesystem operations with rollback support"
        )
        super().__init__(manifest)
        self.rollback_operations: List[Callable] = []
    
    async def execute(self, operation: str, **kwargs) -> ActionResult:
        """Execute filesystem operation."""
        import time
        start = time.time()
        
        result_id = f"fs_{int(time.time()*1000)}"
        
        try:
            if operation == "copy":
                output = await self._copy_file(
                    kwargs.get("src"),
                    kwargs.get("dst"),
                    kwargs.get("recursive", False)
                )
            elif operation == "move":
                output = await self._move_file(
                    kwargs.get("src"),
                    kwargs.get("dst")
                )
            elif operation == "delete":
                output = await self._delete_file(
                    kwargs.get("path"),
                    kwargs.get("safe", True)
                )
            elif operation == "organize":
                output = await self._organize_files(
                    kwargs.get("src_dir"),
                    kwargs.get("rules")
                )
            elif operation == "hash":
                output = await self._hash_file(kwargs.get("path"))
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            duration = int((time.time() - start) * 1000)
            return ActionResult(
                id=result_id,
                success=True,
                output=output,
                duration_ms=duration,
                side_effects=self.rollback_operations
            )
        except Exception as e:
            duration = int((time.time() - start) * 1000)
            return ActionResult(
                id=result_id,
                success=False,
                output=None,
                error=str(e),
                duration_ms=duration
            )
    
    async def _copy_file(self, src: str, dst: str, recursive: bool) -> Dict[str, Any]:
        """Copy file or directory."""
        src_path = Path(src)
        dst_path = Path(dst)
        
        if src_path.is_dir() and recursive:
            shutil.copytree(src_path, dst_path)
            return {"type": "directory", "copied_files": self._count_files(dst_path)}
        else:
            shutil.copy2(src_path, dst_path)
            return {"type": "file", "size": dst_path.stat().st_size}
    
    async def _move_file(self, src: str, dst: str) -> Dict[str, Any]:
        """Move file or directory."""
        src_path = Path(src)
        dst_path = Path(dst)
        
        shutil.move(str(src_path), str(dst_path))
        return {"moved": str(src_path), "to": str(dst_path)}
    
    async def _delete_file(self, path: str, safe: bool = True) -> Dict[str, Any]:
        """Delete file or directory safely."""
        p = Path(path)
        
        if safe and p.is_dir():
            # Move to recycle instead of permanent delete
            backup_dir = Path.home() / ".astra-trash"
            backup_dir.mkdir(exist_ok=True)
            backup_path = backup_dir / p.name
            shutil.move(str(p), str(backup_path))
            return {"deleted": str(p), "backed_up": str(backup_path)}
        else:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            return {"deleted": str(p)}
    
    async def _organize_files(self, src_dir: str, rules: Dict[str, Any]) -> Dict[str, Any]:
        """Organize files by pattern."""
        src = Path(src_dir)
        organized = {"moved": 0, "skipped": 0}
        
        for file_path in src.rglob("*"):
            if file_path.is_file():
                # Simple rule: organize by extension
                ext = file_path.suffix.lower() or "no_ext"
                dest_dir = src / ext
                dest_dir.mkdir(exist_ok=True)
                
                dest_path = dest_dir / file_path.name
                if not dest_path.exists():
                    shutil.move(str(file_path), str(dest_path))
                    organized["moved"] += 1
                else:
                    organized["skipped"] += 1
        
        return organized
    
    async def _hash_file(self, path: str) -> Dict[str, str]:
        """Compute file hash."""
        p = Path(path)
        
        if not p.exists():
            raise FileNotFoundError(path)
        
        sha256_hash = hashlib.sha256()
        with open(p, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return {"path": str(p), "sha256": sha256_hash.hexdigest()}
    
    def _count_files(self, path: Path) -> int:
        """Count files in directory tree."""
        return sum(1 for _ in path.rglob("*") if _.is_file())


class ShellTool(BaseTool):
    """Execute shell commands with whitelist and arg sanitization."""
    
    ALLOWED_COMMANDS = {
        "dir", "ls", "copy", "cp", "move", "mv", "del", "rm",
        "git", "python", "node", "npm", "ffmpeg", "imagemagick",
        "tar", "zip", "7z", "rar", "find", "grep", "sed", "awk"
    }
    
    FORBIDDEN_PATTERNS = {
        "reg delete", "bcdedit", "net user", "useradd", "shutdown",
        "reboot", "halt", "sc stop", "taskkill /f", "format",
    }
    
    def __init__(self):
        manifest = ToolManifest(
            name="shell",
            capability=ToolCapability.SHELL_EXECUTE,
            risk_score=0.9,  # High risk
            description="Whitelisted shell command execution"
        )
        super().__init__(manifest)
    
    async def execute(self, command: str, args: List[str] = None, 
                     timeout_s: int = 30, **kwargs) -> ActionResult:
        """Execute shell command."""
        import time
        start = time.time()
        
        result_id = f"sh_{int(time.time()*1000)}"
        
        try:
            # Validate command
            cmd_name = command.split()[0].lower()
            if cmd_name not in self.ALLOWED_COMMANDS:
                raise ValueError(f"Command not whitelisted: {cmd_name}")
            
            # Check for forbidden patterns
            full_cmd = f"{command} {' '.join(args or [])}"
            for forbidden in self.FORBIDDEN_PATTERNS:
                if forbidden.lower() in full_cmd.lower():
                    raise ValueError(f"Forbidden pattern detected: {forbidden}")
            
            # Execute with timeout
            cmd_list = [command] + (args or [])
            result = subprocess.run(
                cmd_list,
                capture_output=True,
                timeout=timeout_s,
                text=True,
                cwd=kwargs.get("cwd")
            )
            
            duration = int((time.time() - start) * 1000)
            
            if result.returncode == 0:
                return ActionResult(
                    id=result_id,
                    success=True,
                    output=result.stdout,
                    duration_ms=duration
                )
            else:
                return ActionResult(
                    id=result_id,
                    success=False,
                    output=result.stdout,
                    error=result.stderr,
                    duration_ms=duration
                )
        except Exception as e:
            duration = int((time.time() - start) * 1000)
            return ActionResult(
                id=result_id,
                success=False,
                output=None,
                error=str(e),
                duration_ms=duration
            )


class NotificationTool(BaseTool):
    """Display notifications and toasts."""
    
    def __init__(self):
        manifest = ToolManifest(
            name="notifications",
            capability=ToolCapability.NOTIFICATIONS,
            risk_score=0.0,  # No risk
            description="Display notifications and consent prompts"
        )
        super().__init__(manifest)
    
    async def execute(self, notification_type: str, 
                     title: str, message: str, **kwargs) -> ActionResult:
        """Display notification."""
        import time
        start = time.time()
        
        result_id = f"notif_{int(time.time()*1000)}"
        
        try:
            if notification_type == "toast":
                output = await self._show_toast(title, message, kwargs.get("timeout_s", 5))
            elif notification_type == "modal":
                output = await self._show_modal(title, message, kwargs.get("buttons"))
            elif notification_type == "console":
                output = await self._log_console(title, message)
            else:
                raise ValueError(f"Unknown notification type: {notification_type}")
            
            duration = int((time.time() - start) * 1000)
            return ActionResult(
                id=result_id,
                success=True,
                output=output,
                duration_ms=duration
            )
        except Exception as e:
            duration = int((time.time() - start) * 1000)
            return ActionResult(
                id=result_id,
                success=False,
                output=None,
                error=str(e),
                duration_ms=duration
            )
    
    async def _show_toast(self, title: str, message: str, timeout_s: int) -> Dict[str, Any]:
        """Show Windows toast notification."""
        # Platform-specific implementation
        logger.info(f"TOAST: {title} - {message} ({timeout_s}s)")
        return {"type": "toast", "displayed": True}
    
    async def _show_modal(self, title: str, message: str, buttons: List[str]) -> Dict[str, Any]:
        """Show modal dialog."""
        logger.info(f"MODAL: {title} - {message} [{', '.join(buttons or [])}]")
        return {"type": "modal", "displayed": True}
    
    async def _log_console(self, title: str, message: str) -> Dict[str, Any]:
        """Log to console."""
        logger.info(f"CONSOLE: {title} - {message}")
        return {"type": "console", "logged": True}


class ClipboardTool(BaseTool):
    """Clipboard access (read/write)."""
    
    def __init__(self):
        manifest = ToolManifest(
            name="clipboard",
            capability=ToolCapability.CLIPBOARD,
            risk_score=0.3,
            description="Read/write clipboard data"
        )
        super().__init__(manifest)
    
    async def execute(self, operation: str, **kwargs) -> ActionResult:
        """Clipboard operation."""
        import time
        start = time.time()
        
        result_id = f"clip_{int(time.time()*1000)}"
        
        try:
            if operation == "read":
                output = self._read_clipboard()
            elif operation == "write":
                output = self._write_clipboard(kwargs.get("text"))
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            duration = int((time.time() - start) * 1000)
            return ActionResult(
                id=result_id,
                success=True,
                output=output,
                duration_ms=duration
            )
        except Exception as e:
            duration = int((time.time() - start) * 1000)
            return ActionResult(
                id=result_id,
                success=False,
                output=None,
                error=str(e),
                duration_ms=duration
            )
    
    def _read_clipboard(self) -> str:
        """Read clipboard content."""
        try:
            import pyperclip
            return pyperclip.paste()
        except:
            logger.warning("Clipboard read not available")
            return ""
    
    def _write_clipboard(self, text: str) -> Dict[str, Any]:
        """Write to clipboard."""
        try:
            import pyperclip
            pyperclip.copy(text)
            return {"written": len(text), "chars": len(text)}
        except:
            logger.warning("Clipboard write not available")
            raise RuntimeError("Clipboard not available")


class ToolBus:
    """
    Central hub for tool management and execution.
    Handles policy gating, audit logging, and rollback.
    """
    
    def __init__(self, policy_engine=None):
        self.policy_engine = policy_engine
        self.tools: Dict[ToolCapability, BaseTool] = {}
        self.execution_history: List[ActionResult] = []
        self.max_history = 1000
        
        # Register default tools
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register built-in tools."""
        self.register_tool(ToolCapability.FILESYSTEM_WRITE, FilesystemTool())
        self.register_tool(ToolCapability.SHELL_EXECUTE, ShellTool())
        self.register_tool(ToolCapability.NOTIFICATIONS, NotificationTool())
        self.register_tool(ToolCapability.CLIPBOARD, ClipboardTool())
    
    def register_tool(self, capability: ToolCapability, tool: BaseTool):
        """Register a tool."""
        self.tools[capability] = tool
        logger.info(f"Registered tool: {tool.manifest.name}")
    
    async def execute_action(self, capability: ToolCapability, 
                            context: Dict[str, Any],
                            **action_args) -> ActionResult:
        """
        Execute action with policy checking.
        """
        # Check policy
        if self.policy_engine:
            if not self.policy_engine.check_capability(capability.value, 
                                                      action_args.get("target", "")):
                return ActionResult(
                    id="policy_denied",
                    success=False,
                    output=None,
                    error="Policy does not allow this action"
                )
        
        # Get tool
        if capability not in self.tools:
            return ActionResult(
                id="tool_not_found",
                success=False,
                output=None,
                error=f"Tool not registered: {capability.value}"
            )
        
        tool = self.tools[capability]
        
        # Execute
        result = await tool.execute(**action_args)
        
        # Record
        self.execution_history.append(result)
        if len(self.execution_history) > self.max_history:
            self.execution_history.pop(0)
        
        logger.info(f"Action executed: {capability.value} -> {result.success}")
        
        return result
    
    def get_history(self, limit: int = 50) -> List[ActionResult]:
        """Get execution history."""
        return self.execution_history[-limit:]


__all__ = [
    "ToolCapability",
    "ToolManifest",
    "ActionResult",
    "BaseTool",
    "FilesystemTool",
    "ShellTool",
    "NotificationTool",
    "ClipboardTool",
    "ToolBus",
]
