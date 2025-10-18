"""
ASTRA Bridge Configuration
Environment-driven guardrails for safe, observable bridge operations.
"""
from pydantic import BaseModel
import os


class BridgeConfig(BaseModel):
    """Bridge module configuration with Windows-safe defaults."""
    
    enabled: bool = (os.environ.get("ASTRA_BRIDGE_ENABLED", "true").lower() == "true")
    interpret_conf_threshold: float = float(os.environ.get("ASTRA_BRIDGE_INTERPRET_CONF_THRESHOLD", "0.65"))
    max_toolcalls_per_req: int = int(os.environ.get("ASTRA_BRIDGE_MAX_TOOLCALLS_PER_REQ", "1"))
    safe_tools_glob: str = os.environ.get("ASTRA_BRIDGE_SAFE_TOOLS", "scripts/approved/*.ps1")
    mem_ttl_days: int = int(os.environ.get("ASTRA_BRIDGE_MEM_TTL_DAYS", "90"))
    mem_importance_base: float = float(os.environ.get("ASTRA_BRIDGE_MEM_IMPORTANCE_BASE", "0.5"))
    fact_maxlen: int = int(os.environ.get("ASTRA_BRIDGE_FACT_MAXLEN", "512"))
    
    # Windows-specific paths
    bridge_data_dir: str = os.environ.get("ASTRA_BRIDGE_DATA_DIR", "data/bridge")
    
    class Config:
        frozen = False  # Allow runtime updates
