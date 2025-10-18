"""
LSP Bridge (Optional)
Minimal facade to talk to language servers if installed.
Keeps interface simple for ASTRA without caring about backend.
"""

from typing import Optional, List, Dict


class LSPBridge:
    """Optional language server protocol bridge."""
    
    def hover(self, path: str, line: int, col: int) -> Optional[str]:
        """Get hover information at position."""
        return None  # stub
    
    def diagnostics(self, path: str) -> List[Dict]:
        """Get diagnostics (errors/warnings) for file."""
        return []
    
    def format(self, path: str) -> Optional[str]:
        """Format file and return formatted content."""
        return None
