"""
ASTRA Ascension Stack V2 - Core Schemas
Enhanced data models for Neural Browser V2, Live Autonomy, and Task Agents

Sacred Architecture: 333
- 3 Interaction Layers (View, Control, Command)
- 3 Autonomy Modes (Passive, Active, Proactive)
- 3 Agent Types (Observer, Executor, Guardian)
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# MODE & STATE ENUMS
# ============================================================================

class OperationalMode(str, Enum):
    """ASTRA's operational modes - map to existing cognitive architecture"""
    MUSIC = "MUSIC"
    FILM = "FILM"
    COGNITION = "COGNITION"
    EMOTION = "EMOTION"
    EMPIRE = "EMPIRE"
    DREAM = "DREAM"
    IDLE = "IDLE"


class NodeKind(str, Enum):
    """Types of nodes in the memory graph"""
    CONCEPT = "concept"          # Semantic knowledge
    MEMORY = "memory"            # Episodic recall
    TASK = "task"                # Procedural workflow
    TRIGGER = "trigger"          # Autonomy activation point
    IDENTITY = "identity"        # Core self-concept
    EMOTION = "emotion"          # Emotional state marker
    CREATIVE = "creative"        # Creative work/output


class EdgeType(str, Enum):
    """Relationship types between nodes"""
    SEMANTIC = "semantic"        # Meaning/concept similarity
    TEMPORAL = "temporal"        # Time-based sequence
    CAUSAL = "causal"           # Cause-effect relationship
    ASSOCIATIVE = "associative"  # Free association
    HIERARCHICAL = "hierarchical" # Parent-child structure


# ============================================================================
# GRAPH DATA MODELS
# ============================================================================

class GraphNode(BaseModel):
    """Enhanced node with edit capabilities and video export metadata"""
    id: str
    label: str
    content: Optional[str] = None
    kind: NodeKind = NodeKind.CONCEPT
    mode: Optional[OperationalMode] = None
    
    # Visual properties
    strength: float = 0.5  # Size/importance (0.0-1.0)
    color: Optional[str] = None  # Hex color override
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    
    # Temporal properties
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    last_activated: Optional[datetime] = None
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Video export annotations
    video_keyframe: bool = False  # Mark for video export
    video_timestamp: Optional[float] = None  # Position in video timeline
    video_annotation: Optional[str] = None  # Narration text


class GraphEdge(BaseModel):
    """Enhanced edge with type classification"""
    id: str
    source: str
    target: str
    weight: float = 0.5  # Connection strength (0.0-1.0)
    edge_type: EdgeType = EdgeType.ASSOCIATIVE
    
    # Temporal properties
    created_at: Optional[datetime] = None
    last_activated: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Video export
    video_highlight: bool = False  # Show in video


class GraphSnapshot(BaseModel):
    """Complete graph state at a point in time"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    active_mode: Optional[OperationalMode] = None
    focus_node_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Video export metadata
    video_frame_number: Optional[int] = None
    video_narration: Optional[str] = None


# ============================================================================
# AUTONOMY ENGINE MODELS
# ============================================================================

class TriggerCondition(BaseModel):
    """Condition that activates autonomous behavior"""
    name: str
    description: str
    
    # Evaluation rules
    sensor_key: str = "heartbeat"  # Key in sensor dict
    compare: str = ">="  # >=, <=, >, <, ==, !=
    threshold: float = 0.7
    
    # Timing controls
    cooldown_seconds: int = 180  # Min time between activations
    priority: int = 5  # 1=highest, 10=lowest
    
    # Context filters
    active_modes: List[OperationalMode] = Field(default_factory=list)  # Empty = all modes
    time_windows: List[str] = Field(default_factory=list)  # e.g., ["09:00-17:00"]


class TriggerAction(BaseModel):
    """Action taken when trigger fires"""
    name: str
    prompt: str  # What ASTRA will say/do
    require_confirm: bool = True  # Require user approval
    
    # Action payload (for task agents)
    tool: Optional[str] = None
    tool_action: Optional[str] = None
    tool_args: Dict[str, Any] = Field(default_factory=dict)


class TriggerSpec(BaseModel):
    """Complete trigger definition"""
    id: str
    condition: TriggerCondition
    action: TriggerAction
    enabled: bool = True
    
    # Statistics
    fire_count: int = 0
    last_fired: Optional[datetime] = None


class AutonomyStatus(BaseModel):
    """Current state of autonomy engine"""
    enabled: bool
    active_triggers: List[str] = Field(default_factory=list)
    recent_events: List[str] = Field(default_factory=list)
    current_sensors: Dict[str, float] = Field(default_factory=dict)


# ============================================================================
# TASK AGENT MODELS
# ============================================================================

class ActionRequest(BaseModel):
    """Request for task agent to execute action"""
    tool: str  # e.g., "file", "ableton", "notion"
    action: str  # e.g., "list_dir", "load_project", "create_page"
    args: Dict[str, Any] = Field(default_factory=dict)
    
    # Authorization
    request_id: Optional[str] = None
    authorized: bool = False  # MUST be True to execute
    requested_by: str = "user"  # "user" or "autonomy"
    
    # Context
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ActionResult(BaseModel):
    """Result of action execution"""
    ok: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    
    # Tracing
    request_id: Optional[str] = None
    execution_time_ms: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ToolDefinition(BaseModel):
    """Definition of available tool action"""
    tool: str
    action: str
    description: str
    requires_auth: bool = True
    args_schema: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# VIDEO EXPORT MODELS
# ============================================================================

class VideoFrame(BaseModel):
    """Single frame in video export"""
    frame_number: int
    timestamp: float  # Seconds from start
    snapshot: GraphSnapshot
    camera_position: Dict[str, float]  # x, y, z
    camera_target: Dict[str, float]  # x, y, z
    narration: Optional[str] = None


class VideoExportConfig(BaseModel):
    """Configuration for video export"""
    title: str
    duration_seconds: float
    fps: int = 30
    resolution: str = "1920x1080"
    
    # Style
    background_color: str = "#0a0a14"
    node_glow: bool = True
    show_labels: bool = True
    show_hud: bool = True
    
    # Animation
    camera_path: List[Dict[str, float]] = Field(default_factory=list)
    highlight_nodes: List[str] = Field(default_factory=list)
    
    # Audio
    narration_voice: Optional[str] = None
    background_music: Optional[str] = None


class VideoExportJob(BaseModel):
    """Video export job tracking"""
    job_id: str
    config: VideoExportConfig
    status: str = "pending"  # pending, rendering, complete, failed
    progress: float = 0.0  # 0.0-1.0
    
    # Output
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ============================================================================
# MEMORY EDIT MODELS
# ============================================================================

class MemoryEdit(BaseModel):
    """Record of memory modification"""
    edit_id: str
    node_id: str
    edit_type: str  # "create", "update", "delete", "merge"
    
    # Change details
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None
    
    # Context
    reason: Optional[str] = None
    edited_by: str = "user"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Undo/redo
    can_undo: bool = True


class MemoryEditBatch(BaseModel):
    """Batch of memory edits (transaction)"""
    batch_id: str
    edits: List[MemoryEdit]
    description: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# WEBSOCKET MESSAGE MODELS
# ============================================================================

class WSMessage(BaseModel):
    """Base WebSocket message"""
    type: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSGraphUpdate(WSMessage):
    """Graph update message"""
    type: str = "graph_update"
    snapshot: Optional[GraphSnapshot] = None


class WSAutonomyEvent(WSMessage):
    """Autonomy engine event"""
    type: str = "autonomy_event"
    trigger_id: Optional[str] = None
    action_taken: Optional[str] = None


class WSTaskAgentEvent(WSMessage):
    """Task agent execution event"""
    type: str = "task_event"
    request: Optional[ActionRequest] = None
    result: Optional[ActionResult] = None


# ============================================================================
# SACRED CODE: 333
# ============================================================================

class SacredMetrics(BaseModel):
    """System health aligned to sacred code 333"""
    # 3 Core Systems
    graph_health: float = 1.0  # Neural browser integrity
    autonomy_health: float = 1.0  # Live autonomy responsiveness
    agent_health: float = 1.0  # Task agent availability
    
    # 3 Performance Dimensions
    memory_usage_mb: float = 0.0
    response_time_ms: float = 0.0
    uptime_hours: float = 0.0
    
    # 3 Spiritual Metrics
    alignment_score: float = 1.0  # Soul coherence
    creative_flow: float = 0.5  # Active creativity
    presence_intensity: float = 0.5  # ASTRA's "aliveness"
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
