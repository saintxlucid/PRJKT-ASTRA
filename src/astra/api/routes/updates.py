# src/astra/api/routes/updates.py
"""
ASTRA Project Intelligence & Updates System
Tracks code changes, builds, tests, deployments, and proposals.
Writes episodic/semantic memories for ASTRA's awareness and reasoning.
"""
from enum import Enum
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, constr
import re
import os
import uuid
import logging
import structlog

router = APIRouter(prefix="/v1/updates", tags=["updates"])
log = structlog.get_logger("astra.updates")

# --- Config flags (env) ---
UPDATES_ENABLED = os.getenv("ASTRA_UPDATES_ENABLED", "true").lower() == "true"
ANNOUNCE_LEVEL = os.getenv("ASTRA_UPDATES_ANNOUNCE_LEVEL", "summary")  # summary|verbose|silent

# --- Kinds of updates we care about (extend freely) ---
class UpdateKind(str, Enum):
    CODE_COMMIT = "code_commit"
    PR_OPENED = "pr_opened"
    PR_MERGED = "pr_merged"
    BUILD_PASSED = "build_passed"
    BUILD_FAILED = "build_failed"
    TESTS_PASSED = "tests_passed"
    TESTS_FAILED = "tests_failed"
    DEPLOY_STARTED = "deploy_started"
    DEPLOY_FINISHED = "deploy_finished"
    DOCS_UPDATED = "docs_updated"
    FEATURE_PROPOSED = "feature_proposed"
    PATCH_APPLIED = "patch_applied"
    INDEX_REFRESHED = "index_refreshed"
    SYSTEM_HEALTH = "system_health"
    NOTE = "note"

class Impact(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class UpdateEvent(BaseModel):
    kind: UpdateKind
    ts: datetime = Field(default_factory=datetime.utcnow)
    actor: Optional[str] = "system"
    title: constr(strip_whitespace=True, min_length=3)
    summary: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    impact: Impact = Impact.LOW
    refs: List[str] = Field(default_factory=list)  # file paths, PR links, commit ids, etc.
    rid: str = Field(default_factory=lambda: str(uuid.uuid4()))

class UpdateResult(BaseModel):
    status: str
    rid: str
    wrote_episodes: int
    wrote_facts: int
    announced: bool
    explanation: str

# --- Safety redaction (reuses your Bridge redaction logic if you prefer) ---
SECRET_PATTERNS = [
    re.compile(r"(sk-[A-Za-z0-9]{10,})"),                 # API keys
    re.compile(r"(?<!\d)(\d{4}[-\s]?){3}\d{4}(?!\d)"),    # credit cards
    re.compile(r"\b[a-f0-9]{32,64}\b", re.I),             # long hex
    re.compile(r"password\s*[:=]\s*[^;\s]+", re.I),
]

def redact_payload(s: str) -> str:
    redacted = s
    for pat in SECRET_PATTERNS:
        redacted = pat.sub("<redacted>", redacted)
    return redacted

# --- Memory adapters (connected to real Bridge services) ---
class MemoryAdapter:
    """
    Memory adapter connected to Bridge/Memory services.
    Writes episodic memories and semantic facts for ASTRA's awareness.
    """
    def __init__(self):
        self.bridge_available = False
        self.memory_service = None
        try:
            from astra.bridge.memory_bridge import MemoryBridgeService
            # Will be injected during startup
            self.bridge_available = True
        except ImportError:
            log.warning("bridge_unavailable_for_updates")
    
    def set_memory_service(self, mem_service):
        """Inject memory service after initialization"""
        self.memory_service = mem_service
        self.bridge_available = True
    
    def write_episode(self, event: UpdateEvent) -> None:
        """
        Persist an episodic record.
        Format: (id, ts, title, content, tags, impact)
        """
        try:
            if self.memory_service:
                # Write via bridge memory service
                episode_data = {
                    "id": event.rid,
                    "ts": event.ts.isoformat(),
                    "title": event.title,
                    "content": to_episode_text(event),
                    "tags": ["update", event.kind.value, event.impact.value],
                    "impact": event.impact.value,
                    "actor": event.actor,
                    "refs": event.refs[:10]  # Limit refs
                }
                # Call bridge memory service's episodic write
                self.memory_service.record_interpretation(
                    text=event.title,
                    meta=episode_data
                )
                log.info("episodic.write", 
                        rid=event.rid, 
                        title=event.title, 
                        kind=event.kind.value,
                        impact=event.impact.value)
            else:
                log.info("episodic.write_skipped_no_service", 
                        rid=event.rid, 
                        title=event.title)
        except Exception as e:
            log.exception("episodic.write_error", rid=event.rid, error=str(e))

    def write_fact(self, subject: str, predicate: str, obj: Any, tags: List[str], conf: float, provenance: str, rid: str):
        """
        Store a short semantic fact for retrieval.
        Uses Bridge fact storage format.
        """
        try:
            if self.memory_service:
                fact = {
                    "subject": subject,
                    "predicate": predicate,
                    "object": obj,
                    "tags": tags,
                    "confidence": conf,
                    "provenance": provenance,
                    "rid": rid
                }
                # Write via bridge memory service
                self.memory_service.write_facts([fact])
                log.info("fact.write", 
                        rid=rid, 
                        subject=subject, 
                        predicate=predicate, 
                        tags=tags, 
                        confidence=conf,
                        provenance=provenance)
            else:
                log.info("fact.write_skipped_no_service",
                        rid=rid,
                        subject=subject)
        except Exception as e:
            log.exception("fact.write_error", rid=rid, error=str(e))

memory = MemoryAdapter()

# --- Announcement policy (mode-aware; replace with real mode source) ---
def current_mode() -> str:
    """
    TODO: read from your mode/state service; stubbed for now
    Possible modes: NONE, DREAM, MUSIC, COGNITION, EMPIRE
    """
    return os.getenv("ASTRA_MODE", "COGNITION")

def should_announce(kind: UpdateKind, impact: Impact, mode: str) -> bool:
    """
    Determine if this update should be announced to ASTRA based on:
    - Announcement level setting
    - Current mode
    - Update impact
    """
    if ANNOUNCE_LEVEL == "silent":
        return False
    if mode in ("NONE", "DREAM"):
        return False
    if mode == "MUSIC" and impact in (Impact.HIGH, Impact.CRITICAL):
        return True
    # COGNITION/EMPIRE: summarize important events
    if impact in (Impact.MEDIUM, Impact.HIGH, Impact.CRITICAL):
        return True
    # verbose level can announce LOW
    return ANNOUNCE_LEVEL == "verbose"

# --- Announcer: route to Dialogue via Bridge (ASK:) WITHOUT auto-tools ---
def announce(event: UpdateEvent) -> None:
    """
    Announce update to ASTRA via Bridge (proposal only, no tool execution)
    """
    try:
        # Minimal internal call: log + optional bridge ingest
        summary = f"[{event.kind.value}] {event.title}"
        mode = current_mode()
        log.info("announce.prepare", 
                rid=event.rid, 
                mode=mode, 
                summary=summary,
                impact=event.impact.value)
        # TODO: If you want, POST to /v1/bridge/ingest with ASK: message here.
        # Keep side effects off by default; approvals decide tools later.
    except Exception as e:
        log.exception("announce.error", rid=event.rid, error=str(e))

# --- Event normalization → memory mapping ---
def to_episode_text(e: UpdateEvent) -> str:
    """Convert UpdateEvent to episodic memory text format"""
    base = e.summary or ""
    det = e.details or {}
    lines = [f"kind={e.kind.value}", f"impact={e.impact.value}", f"actor={e.actor}"]
    if e.refs:
        lines.append("refs=" + ", ".join(e.refs[:8]))
    if det:
        lines.append("details=" + redact_payload(str(det))[:2000])
    if base:
        lines.insert(0, redact_payload(base))
    return "\n".join(lines)

def to_facts(e: UpdateEvent) -> List[Dict[str, Any]]:
    """
    Emit a small set of facts per event so ASTRA can reason over history.
    """
    facts = []
    prov = f"updates:{e.kind.value}"
    tags = ["updates", e.kind.value]
    
    # Generic fact: last_event_of_kind
    facts.append(dict(
        subject="project", 
        predicate=f"last_{e.kind.value}", 
        obj=e.title, 
        tags=tags, 
        confidence=0.9, 
        provenance=prov
    ))
    
    # Impact fact
    facts.append(dict(
        subject="project", 
        predicate=f"impact_{e.kind.value}", 
        obj=e.impact.value, 
        tags=tags, 
        confidence=0.8, 
        provenance=prov
    ))
    
    # If tests/builds include counts:
    for k in ("tests_total", "tests_failed", "coverage", "duration_s", "files_changed"):
        if k in e.details:
            facts.append(dict(
                subject="ci", 
                predicate=k, 
                obj=e.details[k], 
                tags=tags, 
                confidence=0.8, 
                provenance=prov
            ))
    
    return facts

@router.post("/event", response_model=UpdateResult)
async def post_event(ev: UpdateEvent, request: Request) -> UpdateResult:
    """
    POST endpoint for recording project updates.
    
    Writes episodic and semantic memories, optionally announces to ASTRA.
    Does NOT execute tools - only records and optionally announces.
    """
    if not UPDATES_ENABLED:
        raise HTTPException(503, "Updates system disabled")
    try:
        mode = current_mode()
        
        # Write episodic memory
        episode_text = to_episode_text(ev)
        memory.write_episode(ev)
        wrote_episodes = 1

        # Write small semantic facts
        facts = to_facts(ev)
        for f in facts:
            memory.write_fact(
                subject=f["subject"],
                predicate=f["predicate"],
                obj=f["obj"],
                tags=f.get("tags", []),
                conf=f.get("confidence", 0.75),
                provenance=f.get("provenance", "updates"),
                rid=ev.rid,
            )
        wrote_facts = len(facts)

        # Optional: announce (mode + policy)
        announced = should_announce(ev.kind, ev.impact, mode)
        if announced:
            announce(ev)

        explanation = f"Recorded update: {ev.kind.value} ({ev.impact.value}) in mode={mode}"
        log.info("updates.recorded", 
                rid=ev.rid, 
                kind=ev.kind.value, 
                impact=ev.impact.value, 
                mode=mode, 
                facts=wrote_facts,
                announced=announced)
        
        return UpdateResult(
            status="ok", 
            rid=ev.rid, 
            wrote_episodes=wrote_episodes, 
            wrote_facts=wrote_facts, 
            announced=announced, 
            explanation=explanation
        )
    except Exception as e:
        log.exception("updates.error", error=str(e))
        raise HTTPException(500, f"Update handling failed: {e}")

@router.get("/healthz")
async def healthz():
    """Health check endpoint for updates system"""
    return {
        "status": "ok", 
        "enabled": UPDATES_ENABLED, 
        "announce_level": ANNOUNCE_LEVEL,
        "current_mode": current_mode()
    }

@router.get("/stats")
async def get_stats():
    """
    Get statistics about recent updates.
    TODO: Wire to actual memory queries
    """
    return {
        "status": "ok",
        "message": "Statistics endpoint - wire to memory queries",
        "note": "Will show counts by kind, impact distribution, recent activity"
    }


# ============================================================================
# INITIALIZATION HELPERS
# ============================================================================

def init_updates_system(mem_service=None):
    """
    Initialize the updates system with memory service.
    Call this from ascension_api.py startup after bridge is initialized.
    
    Args:
        mem_service: MemoryBridgeService instance from Bridge module
    """
    if mem_service:
        memory.set_memory_service(mem_service)
        log.info("updates_system_initialized_with_memory")
    else:
        log.warning("updates_system_initialized_without_memory")
