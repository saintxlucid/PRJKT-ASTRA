"""
ASTRA Core Backend Server
FastAPI-based backend for Pantheon UI integration
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import json
import logging
import numpy as np

# Import embedding service for semantic search
from embedding_service import get_embedding_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize embedding service (lazy loading - will be initialized on first use)
embedding_service = None

def _get_embedding_service():
    """Lazy initialize embedding service on first use."""
    global embedding_service
    if embedding_service is None:
        embedding_service = get_embedding_service()
    return embedding_service

app = FastAPI(
    title="ASTRA Core API",
    description="Backend API for ASTRA OS - AI Operating System",
    version="1.0.0"
)

# CORS configuration for Pantheon UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3333", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Data Models ====================

class ChatMessage(BaseModel):
    role: str
    content: str
    agent: Optional[str] = None
    tokens: Optional[int] = None

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    agent_id: str
    stream: bool = False

class ChatResponse(BaseModel):
    message: str
    agent: str
    tokens: int
    timestamp: str

class AgentStatus(BaseModel):
    id: str
    name: str
    status: str
    current_task: Optional[str] = None
    progress: int = 0
    last_active: str

class FlowSession(BaseModel):
    level: int
    duration: int
    phase: str

class VoiceTranscript(BaseModel):
    text: str
    language: str = "en-US"
    confidence: float = 0.95

class Note(BaseModel):
    id: str
    title: str
    content: str
    tags: List[str]
    created: str
    modified: str

class ResearchSource(BaseModel):
    id: str
    title: str
    url: str
    type: str  # 'web', 'file', 'note'
    excerpt: str
    relevance: int

class ResearchProject(BaseModel):
    id: str
    title: str
    query: str
    status: str  # 'active', 'completed'
    sources: List[ResearchSource]
    notes: str
    output: str
    created: str
    modified: str

class BrowserTab(BaseModel):
    id: str
    title: str
    url: str
    favicon: Optional[str] = None

class Bookmark(BaseModel):
    id: str
    title: str
    url: str
    folder: str
    created: str

class HistoryEntry(BaseModel):
    id: str
    title: str
    url: str
    timestamp: str
    visit_count: int

class MemoryLayer(BaseModel):
    layer: int  # 0, 1, 2, or 3
    label: str  # 'L0: Raw', 'L1: Summary', 'L2: Insight', 'L3: Essence'
    memory_count: int
    compression_ratio: float
    last_updated: str

class Memory(BaseModel):
    id: str
    content: str
    layer: int  # 0-3
    embedding: Optional[List[float]] = None
    tags: List[str]
    importance: float  # 0.0-1.0
    created: str
    last_accessed: str
    access_count: int
    source: str  # 'conversation', 'note', 'research', etc.

class MemorySearchResult(BaseModel):
    memory: Memory
    relevance: float
    highlighted_text: str

class TemporalDecayStats(BaseModel):
    total_memories: int
    decayed_memories: int
    avg_importance: float
    decay_rate: float
    last_decay_run: str

# ==================== In-Memory Storage ====================

active_connections: List[WebSocket] = []
agent_states: Dict[str, AgentStatus] = {
    "cognitive-core": AgentStatus(
        id="cognitive-core",
        name="Cognitive Core",
        status="online",
        current_task="Ready for instructions",
        progress=0,
        last_active=datetime.now().isoformat()
    ),
    "memory-weaver": AgentStatus(
        id="memory-weaver",
        name="Memory Weaver",
        status="online",
        current_task="Indexing memories",
        progress=78,
        last_active=datetime.now().isoformat()
    ),
    "research-specialist": AgentStatus(
        id="research-specialist",
        name="Research Specialist",
        status="busy",
        current_task="Deep research on quantum computing",
        progress=45,
        last_active=datetime.now().isoformat()
    ),
    "code-architect": AgentStatus(
        id="code-architect",
        name="Code Architect",
        status="online",
        current_task="Standing by",
        progress=0,
        last_active=datetime.now().isoformat()
    )
}

# ==================== Health Check ====================

@app.get("/")
async def root():
    """Root endpoint - API health check"""
    return {
        "status": "online",
        "service": "ASTRA Core API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "agents": len(agent_states),
        "active_connections": len(active_connections),
        "timestamp": datetime.now().isoformat()
    }

# ==================== Agent Management ====================

@app.get("/api/agents", response_model=List[AgentStatus])
async def get_agents():
    """Get status of all agents"""
    return list(agent_states.values())

@app.get("/api/agents/{agent_id}", response_model=AgentStatus)
async def get_agent(agent_id: str):
    """Get specific agent status"""
    if agent_id not in agent_states:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent_states[agent_id]

# ==================== Chat API ====================

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send message to agent and get response"""
    logger.info(f"Chat request for agent: {request.agent_id}")
    
    if request.agent_id not in agent_states:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = agent_states[request.agent_id]
    
    # Simulate AI response (replace with actual LLM integration)
    last_message = request.messages[-1].content if request.messages else ""
    
    response_text = f"[{agent.name}] I received your message: '{last_message}'. "
    response_text += "This is a demo response. In production, this would connect to the LLM backend."
    
    response = ChatResponse(
        message=response_text,
        agent=agent.name,
        tokens=len(response_text.split()),
        timestamp=datetime.now().isoformat()
    )
    
    # Update agent state
    agent.last_active = datetime.now().isoformat()
    agent.current_task = "Processing chat request"
    
    return response

# ==================== Voice API ====================

@app.post("/api/voice/transcribe")
async def transcribe_audio(audio_data: Dict[str, Any]):
    """Transcribe audio to text (placeholder for Whisper integration)"""
    logger.info("Voice transcription request received")
    
    # Placeholder - integrate with Whisper
    return VoiceTranscript(
        text="This is a demo transcription. Integrate Whisper for real STT.",
        language="en-US",
        confidence=0.95
    )

@app.post("/api/voice/synthesize")
async def synthesize_speech(text: str):
    """Synthesize text to speech (placeholder for TTS integration)"""
    logger.info(f"TTS request: {text[:50]}...")
    
    # Placeholder - integrate with TTS engine
    return {
        "status": "success",
        "audio_url": "/audio/demo.mp3",
        "duration": 2.5,
        "text": text
    }

# ==================== Flow Tracking ====================

@app.get("/api/flow/status")
async def get_flow_status():
    """Get current flow session status"""
    return FlowSession(
        level=67,
        duration=25,
        phase="deep"
    )

@app.post("/api/flow/start")
async def start_flow_session(duration: int = 25):
    """Start a new flow session"""
    logger.info(f"Starting flow session: {duration} minutes")
    return {
        "status": "started",
        "duration": duration,
        "start_time": datetime.now().isoformat()
    }

# ==================== Notes API ====================

notes_db: List[Note] = []

# Research projects storage
research_projects_db: List[ResearchProject] = []

# Browser data storage
bookmarks_db: List[Bookmark] = []
history_db: List[HistoryEntry] = []
tabs_db: List[BrowserTab] = []

# Memory system storage (Dream Grove)
memories_db: List[Memory] = []
memory_layers_stats: Dict[int, MemoryLayer] = {
    0: MemoryLayer(layer=0, label="L0: Raw", memory_count=0, compression_ratio=1.0, last_updated=datetime.now().isoformat()),
    1: MemoryLayer(layer=1, label="L1: Summary", memory_count=0, compression_ratio=0.5, last_updated=datetime.now().isoformat()),
    2: MemoryLayer(layer=2, label="L2: Insight", memory_count=0, compression_ratio=0.2, last_updated=datetime.now().isoformat()),
    3: MemoryLayer(layer=3, label="L3: Essence", memory_count=0, compression_ratio=0.05, last_updated=datetime.now().isoformat())
}
temporal_decay_stats = TemporalDecayStats(
    total_memories=0,
    decayed_memories=0,
    avg_importance=0.0,
    decay_rate=0.01,
    last_decay_run=datetime.now().isoformat()
)

# ==================== Dream Grove Memory API ====================

@app.get("/api/memory/layers", response_model=List[MemoryLayer])
async def get_memory_layers():
    """Get memory layer statistics (L0-L3)"""
    # Update memory counts
    for layer_id in range(4):
        layer_memories = [m for m in memories_db if m.layer == layer_id]
        memory_layers_stats[layer_id].memory_count = len(layer_memories)
        memory_layers_stats[layer_id].last_updated = datetime.now().isoformat()
    
    return list(memory_layers_stats.values())

@app.get("/api/memory/all", response_model=List[Memory])
async def get_all_memories(layer: Optional[int] = None, limit: int = 100):
    """Get all memories, optionally filtered by layer"""
    if layer is not None:
        filtered = [m for m in memories_db if m.layer == layer]
        return filtered[:limit]
    return memories_db[:limit]

@app.get("/api/memory/{memory_id}", response_model=Memory)
async def get_memory(memory_id: str):
    """Get a specific memory by ID"""
    for memory in memories_db:
        if memory.id == memory_id:
            # Update access stats
            memory.last_accessed = datetime.now().isoformat()
            memory.access_count += 1
            return memory
    raise HTTPException(status_code=404, detail="Memory not found")

@app.post("/api/memory", response_model=Memory)
async def create_memory(memory: Memory):
    """Store a new memory"""
    # Generate embedding and index if embedding service available
    try:
        svc = _get_embedding_service()
        if svc is not None:
            # EmbeddingService.encode accepts text and returns numpy array
            emb = svc.encode(memory.content)
            # Store embedding as list[float] for portability
            memory.embedding = emb.tolist() if hasattr(emb, 'tolist') else list(map(float, emb))
            # Add to FAISS index
            try:
                svc.add_to_index(memory.id, emb)
            except Exception as e:
                logger.warning(f"Failed to add memory to index: {e}")
    except Exception as e:
        logger.error(f"Embedding generation failed for memory {memory.id}: {e}")

    memories_db.append(memory)
    logger.info(f"Memory created: {memory.id} (L{memory.layer})")
    return memory

@app.put("/api/memory/{memory_id}", response_model=Memory)
async def update_memory(memory_id: str, memory: Memory):
    """Update an existing memory"""
    for i, existing_memory in enumerate(memories_db):
        if existing_memory.id == memory_id:
            # If content changed, re-embed and update index
            try:
                svc = _get_embedding_service()
                if svc is not None:
                    emb = svc.encode(memory.content)
                    memory.embedding = emb.tolist() if hasattr(emb, 'tolist') else list(map(float, emb))
                    # For simplicity, rebuild index entry by removing and re-adding
                    try:
                        svc.remove_from_index(memory_id)
                    except Exception:
                        pass
                    try:
                        svc.add_to_index(memory.id, emb)
                    except Exception as e:
                        logger.warning(f"Failed to update index for memory {memory_id}: {e}")
            except Exception as e:
                logger.error(f"Embedding update failed for memory {memory_id}: {e}")

            memories_db[i] = memory
            logger.info(f"Memory updated: {memory_id}")
            return memory
    raise HTTPException(status_code=404, detail="Memory not found")

@app.delete("/api/memory/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a memory"""
    global memories_db
    # Remove from in-memory DB
    memories_db = [m for m in memories_db if m.id != memory_id]
    # Remove from index (best-effort)
    try:
        svc = _get_embedding_service()
        if svc is not None:
            svc.remove_from_index(memory_id)
    except Exception as e:
        logger.warning(f"Failed to remove memory {memory_id} from index: {e}")

    logger.info(f"Memory deleted: {memory_id}")
    return {"status": "deleted", "id": memory_id}

@app.post("/api/memory/search", response_model=List[MemorySearchResult])
async def search_memories(query: str, layer: Optional[int] = None, limit: int = 10):
    """Search memories by semantic similarity"""
    results: List[MemorySearchResult] = []

    # Prefer vector search if index is available and has vectors
    try:
        svc = _get_embedding_service()
        if svc is not None and svc.index is not None and svc.memory_ids:
            top_k = min(limit, len(svc.memory_ids))
            search_results = svc.search(query, top_k=top_k)

            # Map results back to Memory objects
            for mem_id, score in search_results:
                # Find the memory object
                mem_obj = next((m for m in memories_db if m.id == mem_id), None)
                if mem_obj is None:
                    continue
                if layer is not None and mem_obj.layer != layer:
                    continue

                highlighted = mem_obj.content[:200]
                results.append(MemorySearchResult(memory=mem_obj, relevance=score, highlighted_text=highlighted))

            # Sort by combined score (score * importance)
            results.sort(key=lambda r: (r.relevance * r.memory.importance), reverse=True)
            return results[:limit]
    except Exception as e:
        logger.warning(f"Vector search failed, falling back to keyword search: {e}")

    # Fallback: simple keyword matching
    query_lower = query.lower()
    for memory in memories_db:
        if layer is not None and memory.layer != layer:
            continue

        content_lower = memory.content.lower()
        if query_lower in content_lower:
            relevance = query_lower.count(' ') + 1
            relevance = min(relevance / 10.0, 1.0)
            start_idx = content_lower.find(query_lower)
            context_start = max(0, start_idx - 50)
            context_end = min(len(memory.content), start_idx + len(query) + 50)
            highlighted = memory.content[context_start:context_end]
            if context_start > 0:
                highlighted = "..." + highlighted
            if context_end < len(memory.content):
                highlighted = highlighted + "..."

            results.append(MemorySearchResult(memory=memory, relevance=relevance, highlighted_text=highlighted))

    results.sort(key=lambda r: (r.relevance * r.memory.importance), reverse=True)
    return results[:limit]

@app.get("/api/memory/decay/stats", response_model=TemporalDecayStats)
async def get_temporal_decay_stats():
    """Get temporal decay statistics"""
    if len(memories_db) > 0:
        total_importance = sum(m.importance for m in memories_db)
        temporal_decay_stats.total_memories = len(memories_db)
        temporal_decay_stats.avg_importance = total_importance / len(memories_db)
    else:
        temporal_decay_stats.total_memories = 0
        temporal_decay_stats.avg_importance = 0.0
    
    temporal_decay_stats.last_decay_run = datetime.now().isoformat()
    return temporal_decay_stats

@app.post("/api/memory/decay/run")
async def run_temporal_decay(decay_rate: float = 0.01):
    """Run temporal decay algorithm on all memories"""
    decayed_count = 0
    now = datetime.now()
    
    for memory in memories_db:
        last_accessed = datetime.fromisoformat(memory.last_accessed)
        time_delta_hours = (now - last_accessed).total_seconds() / 3600
        
        # Decay formula: importance *= exp(-decay_rate * time_delta_hours)
        import math
        decay_factor = math.exp(-decay_rate * time_delta_hours)
        old_importance = memory.importance
        memory.importance = memory.importance * decay_factor
        
        if memory.importance < old_importance:
            decayed_count += 1
    
    logger.info(f"Temporal decay run: {decayed_count} memories decayed")
    temporal_decay_stats.decayed_memories = decayed_count
    temporal_decay_stats.decay_rate = decay_rate
    temporal_decay_stats.last_decay_run = now.isoformat()
    
    return temporal_decay_stats

@app.post("/api/memory/compress")
async def compress_memories(source_layer: int = 0, target_layer: int = 1):
    """Compress memories from one layer to another (e.g., L0 -> L1)"""
    if source_layer >= target_layer:
        raise HTTPException(status_code=400, detail="Source layer must be lower than target layer")
    
    source_memories = [m for m in memories_db if m.layer == source_layer]
    
    if not source_memories:
        return {"status": "no_memories", "compressed": 0}
    
    # Group similar memories (simple grouping by tags for now)
    from collections import defaultdict
    tag_groups = defaultdict(list)
    for memory in source_memories:
        key = tuple(sorted(memory.tags)) if memory.tags else ("untagged",)
        tag_groups[key].append(memory)
    
    compressed_count = 0
    for tag_key, group in tag_groups.items():
        if len(group) >= 3:  # Compress groups of 3+ memories
            # Create compressed memory
            combined_content = " | ".join([m.content[:100] for m in group[:5]])
            compressed_memory = Memory(
                id=f"compressed_{source_layer}_to_{target_layer}_{len(memories_db)}",
                content=f"Summary of {len(group)} memories: {combined_content}",
                layer=target_layer,
                embedding=None,
                tags=list(tag_key) if tag_key != ("untagged",) else [],
                importance=max(m.importance for m in group),
                created=datetime.now().isoformat(),
                last_accessed=datetime.now().isoformat(),
                access_count=0,
                source="compression"
            )
            # Embed compressed memory if possible
            try:
                svc = _get_embedding_service()
                if svc is not None:
                    emb = svc.encode(compressed_memory.content)
                    compressed_memory.embedding = emb.tolist() if hasattr(emb, 'tolist') else list(map(float, emb))
                    try:
                        svc.add_to_index(compressed_memory.id, emb)
                    except Exception as e:
                        logger.warning(f"Failed to index compressed memory: {e}")
            except Exception as e:
                logger.warning(f"Embedding failed for compressed memory: {e}")

            memories_db.append(compressed_memory)
            compressed_count += 1
    
    logger.info(f"Compression: {compressed_count} compressed memories created (L{source_layer} -> L{target_layer})")
    return {"status": "success", "compressed": compressed_count, "source_layer": source_layer, "target_layer": target_layer}

# ==================== Notes API ====================
async def get_notes():
    """Get all notes"""
    return notes_db

@app.post("/api/notes", response_model=Note)
async def create_note(note: Note):
    """Create a new note"""
    notes_db.append(note)
    logger.info(f"Note created: {note.title}")
    return note

@app.put("/api/notes/{note_id}", response_model=Note)
async def update_note(note_id: str, note: Note):
    """Update existing note"""
    for i, existing_note in enumerate(notes_db):
        if existing_note.id == note_id:
            notes_db[i] = note
            logger.info(f"Note updated: {note.title}")
            return note
    raise HTTPException(status_code=404, detail="Note not found")

@app.delete("/api/notes/{note_id}")
async def delete_note(note_id: str):
    """Delete a note"""
    global notes_db
    notes_db = [n for n in notes_db if n.id != note_id]
    logger.info(f"Note deleted: {note_id}")
    return {"status": "deleted", "id": note_id}

# ==================== Research API ====================

@app.get("/api/research/projects", response_model=List[ResearchProject])
async def get_research_projects():
    """Get all research projects"""
    return research_projects_db

@app.get("/api/research/projects/{project_id}", response_model=ResearchProject)
async def get_research_project(project_id: str):
    """Get a specific research project"""
    for project in research_projects_db:
        if project.id == project_id:
            return project
    raise HTTPException(status_code=404, detail="Project not found")

@app.post("/api/research/projects", response_model=ResearchProject)
async def create_research_project(project: ResearchProject):
    """Create a new research project"""
    research_projects_db.append(project)
    logger.info(f"Research project created: {project.title}")
    return project

@app.put("/api/research/projects/{project_id}", response_model=ResearchProject)
async def update_research_project(project_id: str, project: ResearchProject):
    """Update an existing research project"""
    for i, existing_project in enumerate(research_projects_db):
        if existing_project.id == project_id:
            research_projects_db[i] = project
            logger.info(f"Research project updated: {project.title}")
            return project
    raise HTTPException(status_code=404, detail="Project not found")

@app.delete("/api/research/projects/{project_id}")
async def delete_research_project(project_id: str):
    """Delete a research project"""
    global research_projects_db
    research_projects_db = [p for p in research_projects_db if p.id != project_id]
    logger.info(f"Research project deleted: {project_id}")
    return {"status": "deleted", "id": project_id}

# ==================== Browser API ====================

@app.get("/api/browser/bookmarks", response_model=List[Bookmark])
async def get_bookmarks():
    """Get all bookmarks"""
    return bookmarks_db

@app.post("/api/browser/bookmarks", response_model=Bookmark)
async def create_bookmark(bookmark: Bookmark):
    """Create a new bookmark"""
    bookmarks_db.append(bookmark)
    logger.info(f"Bookmark created: {bookmark.title}")
    return bookmark

@app.delete("/api/browser/bookmarks/{bookmark_id}")
async def delete_bookmark(bookmark_id: str):
    """Delete a bookmark"""
    global bookmarks_db
    bookmarks_db = [b for b in bookmarks_db if b.id != bookmark_id]
    logger.info(f"Bookmark deleted: {bookmark_id}")
    return {"status": "deleted", "id": bookmark_id}

@app.get("/api/browser/history", response_model=List[HistoryEntry])
async def get_history():
    """Get browser history"""
    return history_db

@app.post("/api/browser/history", response_model=HistoryEntry)
async def add_history_entry(entry: HistoryEntry):
    """Add a history entry"""
    history_db.append(entry)
    return entry

@app.get("/api/browser/tabs", response_model=List[BrowserTab])
async def get_tabs():
    """Get all open tabs"""
    return tabs_db

@app.post("/api/browser/tabs", response_model=BrowserTab)
async def create_tab(tab: BrowserTab):
    """Create a new tab"""
    tabs_db.append(tab)
    logger.info(f"Tab created: {tab.title}")
    return tab

@app.put("/api/browser/tabs/{tab_id}", response_model=BrowserTab)
async def update_tab(tab_id: str, tab: BrowserTab):
    """Update an existing tab"""
    for i, existing_tab in enumerate(tabs_db):
        if existing_tab.id == tab_id:
            tabs_db[i] = tab
            return tab
    raise HTTPException(status_code=404, detail="Tab not found")

@app.delete("/api/browser/tabs/{tab_id}")
async def delete_tab(tab_id: str):
    """Delete a tab"""
    global tabs_db
    tabs_db = [t for t in tabs_db if t.id != tab_id]
    logger.info(f"Tab deleted: {tab_id}")
    return {"status": "deleted", "id": tab_id}

# ==================== WebSocket for Real-Time Updates ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time agent updates"""
    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"WebSocket connected. Total: {len(active_connections)}")
    
    try:
        # Send initial state
        await websocket.send_json({
            "type": "connected",
            "agents": [agent.dict() for agent in agent_states.values()],
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep connection alive and send periodic updates
        while True:
            # Send agent status updates every 5 seconds
            await asyncio.sleep(5)
            
            # Simulate agent progress updates
            for agent_id, agent in agent_states.items():
                if agent.status == "busy" and agent.progress < 100:
                    agent.progress = min(100, agent.progress + 5)
                    agent.last_active = datetime.now().isoformat()
            
            # Broadcast to this connection
            await websocket.send_json({
                "type": "agent_update",
                "agents": [agent.dict() for agent in agent_states.values()],
                "timestamp": datetime.now().isoformat()
            })
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(active_connections)}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)

# ==================== Broadcast Helper ====================

async def broadcast_message(message: Dict[str, Any]):
    """Broadcast message to all connected WebSocket clients"""
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"Broadcast error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
