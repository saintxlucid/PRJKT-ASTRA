"""
ASTRA Tool Bus Contracts
Core data models and contracts for tool execution.
Created: October 16, 2025
"""
from enum import Enum
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
from pydantic import BaseModel, Field, validator
from datetime import datetime, timedelta

class Capability(str, Enum):
    """Tool capabilities for policy enforcement"""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    FILE_MOVE = "file_move"
    NETWORK_READ = "network_read"
    NETWORK_WRITE = "network_write"
    CODE_EXEC = "code_exec"
    UI_CONTROL = "ui_control"
    SYSTEM_CONFIG = "system_config"

class ExecutionMode(str, Enum):
    """Tool execution modes"""
    SIMULATE = "simulate"
    CONFIRM = "confirm"
    AUTO = "auto"

class SecurityLimits(BaseModel):
    """Tool security constraints"""
    allowed_paths: Optional[List[Path]] = None
    denied_paths: Optional[List[Path]] = None
    allowed_domains: Optional[List[str]] = None
    sandbox: bool = False

    @validator("allowed_paths", "denied_paths", pre=True)
    def convert_paths(cls, v):
        """Convert path strings to Path objects"""
        if v is None:
            return None
        return [Path(p) if isinstance(p, str) else p for p in v]

class ResourceLimits(BaseModel):
    """Tool resource constraints"""
    max_runtime_s: int = 30
    max_output_bytes: int = 1024 * 1024  # 1MB
    max_memory_mb: Optional[int] = None

class ToolSpec(BaseModel):
    """Tool specification"""
    name: str
    version: str
    description: str
    capabilities: Set[Capability]
    args_schema: Dict[str, Any]  # JSON Schema
    limits: ResourceLimits
    security: SecurityLimits

    class Config:
        arbitrary_types_allowed = True

class AlignmentProfile(BaseModel):
    """Alignment and safety settings"""
    risk_tolerance: str = "medium"  # low|medium|high
    consent_rules: Dict[Capability, str]  # capability → consent_level
    red_lines: List[str]

class ConsentToken(BaseModel):
    """Consent grant for tool execution"""
    token: str
    capabilities: Set[Capability]
    scope: str  # global|session|task
    granted_by: str
    expires_at: datetime
    
    @property
    def is_valid(self) -> bool:
        """Check if token is still valid"""
        return datetime.now() < self.expires_at

class ExecutionContext(BaseModel):
    """Tool execution context"""
    trace_id: str
    mode: ExecutionMode
    operator: str
    working_dir: Optional[Path] = None
    consent_token: Optional[ConsentToken] = None
    alignment_profile: AlignmentProfile
    env_overrides: Dict[str, str] = {}

    class Config:
        arbitrary_types_allowed = True

class BackupInfo(BaseModel):
    """Backup operation details"""
    created: bool
    path: Optional[Path] = None
    hash: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

class VerificationInfo(BaseModel):
    """Action verification results"""
    passed: bool
    details: str

class AlignmentMetadata(BaseModel):
    """Alignment decision metadata"""
    labels: List[str]
    impact: str  # low|medium|high
    uncertainty: float
    consent_required: Optional[str] = None
    rationale: Optional[str] = None

class ExecutionStatus(str, Enum):
    """Tool execution status"""
    SUCCESS = "success"
    FAIL = "fail"
    DENIED = "denied"
    SIMULATE_ONLY = "simulate_only"

class ExecutionResult(BaseModel):
    """Tool execution results"""
    status: ExecutionStatus
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    artifacts: List[Path] = []
    verification: VerificationInfo
    backup: Optional[BackupInfo] = None
    alignment_meta: AlignmentMetadata
    error_code: Optional[str] = None  # BUS.TOOL_TIMEOUT, POLICY.RED_LINE, etc.

    class Config:
        arbitrary_types_allowed = True

class PlanStep(BaseModel):
    """Single step in an execution plan"""
    id: str
    tool: str
    args: Dict[str, Any]
    expect: str
    confirm: bool = False
    reversible: bool = True
    alignment_note: str

class Plan(BaseModel):
    """Complete execution plan"""
    goal: str
    steps: List[PlanStep]

    def validate_alignment_notes(self) -> bool:
        """Verify every step has an alignment note"""
        return all(bool(step.alignment_note) for step in self.steps)