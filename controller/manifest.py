"""
Action Manifest - Undo semantics for state-changing operations.

Records all fs.move, window.state, and other state-changing actions to JSONL.
Provides rollback() to execute undo actions in reverse order.

Architecture:
- Each action handler calls manifest.record() with undo info
- Manifest appends to JSONL file with timestamp, action, undo_action
- rollback() reads JSONL in reverse, executes undo actions
- Supports partial rollback (rollback last N actions)

Example:
    manifest = ActionManifest("session_123.jsonl")
    manifest.record("fs.move", {"src": "a.txt", "dst": "b.txt"}, 
                    undo={"action": "fs.move", "args": {"src": "b.txt", "dst": "a.txt"}})
    # Later:
    manifest.rollback()  # Moves b.txt back to a.txt
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class ActionManifest:
    """
    Records state-changing actions with undo information to JSONL.
    
    Thread-safety: Not thread-safe. Use one manifest per session.
    File format: Each line is {"ts": ISO8601, "action": str, "args": dict, "undo": dict}
    """
    
    def __init__(self, manifest_path: str | Path):
        """
        Initialize manifest.
        
        Args:
            manifest_path: Path to JSONL manifest file (created if not exists)
        """
        self.path = Path(manifest_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file if it doesn't exist
        if not self.path.exists():
            self.path.touch()
            logger.info(f"Created manifest: {self.path}")
    
    def record(self, action: str, args: dict[str, Any], undo: dict[str, Any] | None = None) -> None:
        """
        Record an action to the manifest.
        
        Args:
            action: Action name (e.g., "fs.move", "window.state")
            args: Arguments passed to the action
            undo: Undo information with {"action": str, "args": dict} or None if no undo
        
        Example:
            manifest.record("fs.move", {"src": "a.txt", "dst": "b.txt"},
                          undo={"action": "fs.move", "args": {"src": "b.txt", "dst": "a.txt"}})
        """
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "args": args,
            "undo": undo
        }
        
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        
        logger.info(f"Recorded action: {action} (undo={'yes' if undo else 'no'})")
    
    def get_entries(self) -> list[dict[str, Any]]:
        """
        Read all manifest entries.
        
        Returns:
            List of manifest entries (oldest first)
        """
        if not self.path.exists() or self.path.stat().st_size == 0:
            return []
        
        entries = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        logger.warning(f"Skipping malformed manifest line: {e}")
        
        return entries
    
    def rollback(self, count: int | None = None) -> list[dict[str, Any]]:
        """
        Execute undo actions in reverse order.
        
        Args:
            count: Number of actions to rollback (default: all)
        
        Returns:
            List of executed undo actions with results: [{"action": str, "args": dict, "result": dict}, ...]
        
        Example:
            results = manifest.rollback(count=3)  # Undo last 3 actions
            for r in results:
                print(f"{r['action']}: {r['result']}")
        """
        entries = self.get_entries()
        if not entries:
            logger.info("No actions to rollback")
            return []
        
        # Get entries to rollback (reverse order)
        if count is None:
            to_rollback = list(reversed(entries))
        else:
            to_rollback = list(reversed(entries[-count:]))
        
        results = []
        for entry in to_rollback:
            undo = entry.get("undo")
            if not undo:
                logger.info(f"Skipping action without undo: {entry['action']}")
                continue
            
            undo_action = undo.get("action")
            undo_args = undo.get("args", {})
            
            logger.info(f"Rolling back: {entry['action']} via {undo_action}")
            
            # Execute undo action
            try:
                result = self._execute_undo(undo_action, undo_args)
                results.append({
                    "action": undo_action,
                    "args": undo_args,
                    "result": result
                })
            except Exception as e:
                logger.error(f"Undo failed for {undo_action}: {e}")
                results.append({
                    "action": undo_action,
                    "args": undo_args,
                    "result": {"ok": False, "error": str(e)}
                })
        
        logger.info(f"Rollback complete: {len(results)} actions executed")
        return results
    
    def _execute_undo(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """
        Execute an undo action.
        
        Args:
            action: Action to execute (e.g., "fs.move", "window.state")
            args: Arguments for the action
        
        Returns:
            Result dict with {"ok": bool, ...}
        
        Note:
            This is a simplified executor. In production, this should use
            the full dispatch() function with token verification.
        """
        if action == "fs.move":
            return self._undo_fs_move(args)
        elif action == "fs.delete":
            return self._undo_fs_delete(args)
        elif action == "window.state":
            return self._undo_window_state(args)
        else:
            logger.warning(f"Unknown undo action: {action}")
            return {"ok": False, "error": "unknown_action"}
    
    def _undo_fs_move(self, args: dict[str, Any]) -> dict[str, Any]:
        """Undo fs.move by moving file back."""
        src = args.get("src")
        dst = args.get("dst")
        
        if not src or not dst:
            return {"ok": False, "error": "missing_args"}
        
        src_path = Path(src)
        dst_path = Path(dst)
        
        if not src_path.exists():
            return {"ok": False, "error": "src_not_found"}
        
        try:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            src_path.rename(dst_path)
            logger.info(f"Undo fs.move: {src} -> {dst}")
            return {"ok": True, "restored": str(dst_path)}
        except Exception as e:
            logger.error(f"Undo fs.move failed: {e}")
            return {"ok": False, "error": str(e)}
    
    def _undo_fs_delete(self, args: dict[str, Any]) -> dict[str, Any]:
        """Undo fs.delete by restoring from backup."""
        # This requires the delete handler to create a backup first
        backup_path = args.get("backup_path")
        original_path = args.get("original_path")
        
        if not backup_path or not original_path:
            return {"ok": False, "error": "missing_backup_info"}
        
        backup = Path(backup_path)
        original = Path(original_path)
        
        if not backup.exists():
            return {"ok": False, "error": "backup_not_found"}
        
        try:
            original.parent.mkdir(parents=True, exist_ok=True)
            backup.rename(original)
            logger.info(f"Undo fs.delete: restored {original}")
            return {"ok": True, "restored": str(original)}
        except Exception as e:
            logger.error(f"Undo fs.delete failed: {e}")
            return {"ok": False, "error": str(e)}
    
    def _undo_window_state(self, args: dict[str, Any]) -> dict[str, Any]:
        """Undo window.state by restoring previous geometry."""
        # This requires window manager integration (pywinauto)
        # For now, return placeholder
        logger.info(f"Window state restore: {args}")
        return {"ok": True, "note": "window_restore_placeholder"}
    
    def clear(self) -> None:
        """Clear the manifest (delete all entries)."""
        if self.path.exists():
            self.path.unlink()
            self.path.touch()
            logger.info(f"Cleared manifest: {self.path}")
    
    def __len__(self) -> int:
        """Return number of recorded actions."""
        return len(self.get_entries())
    
    def __repr__(self) -> str:
        return f"ActionManifest(path={self.path}, entries={len(self)})"
