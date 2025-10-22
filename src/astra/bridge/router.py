"""
ASTRA Bridge Router
Deterministic routing to Memory/Tool/Reply with metrics.
"""
from typing import Dict, Any
import structlog

from .schemas import BridgeRouteResult
from .config import BridgeConfig
from .memory_bridge import MemoryBridge
from .tool_bridge import ToolBridgeService

logger = structlog.get_logger()


def route(payload: Dict[str, Any], 
          cfg: BridgeConfig, 
          mem: MemoryBridge, 
          tools: ToolBridgeService) -> BridgeRouteResult:
    """
    Route interpreted payload to appropriate handlers:
    - Facts → Memory (LTM)
    - Intents → Memory/Tools/Reply based on kind
    - Track metrics and discarded items
    
    Returns:
        BridgeRouteResult with writes, tool_calls, reply, metrics
    """
    logger.info("bridge_route_start")
    
    writes = []
    tool_calls = []
    reply = None
    discarded = {"intents": 0, "facts": 0}
    
    intents = payload.get("intents", [])
    facts = payload.get("facts", [])
    safe_text = payload.get("safe_text", "")
    
    # Memory write for facts
    if facts:
        logger.info("bridge_route_facts", count=len(facts))
        ids = mem.write_facts(facts)
        writes.extend(ids)
    
    # Single tool call budget (configurable via env)
    budget = cfg.max_toolcalls_per_req
    
    for it in intents:
        kind = it.get("kind")
        args = it.get("args", {})
        confidence = it.get("confidence", 0.0)
        rationale = it.get("rationale", "")
        
        logger.debug("bridge_route_intent", kind=kind, confidence=confidence)
        
        if kind == "act" and budget > 0:
            # Tool execution (DAW, file ops, etc.)
            tool = args.get("tool") or args.get("target") or "ableton"
            action = args.get("action") or "open_project"
            authorized = bool(args.get("authorized", False))
            
            call_res = tools.call_one(tool=tool, action=action, args=args, authorized=authorized)
            tool_calls.append({
                "tool": tool,
                "action": action,
                "result": call_res,
                "confidence": confidence,
                "rationale": rationale
            })
            budget -= 1
            
        elif kind == "ask" and reply is None:
            # Dialogue response
            reply = "Bridge: I heard your request. What do you need next?"
            logger.info("bridge_route_reply_ask")
            
        elif kind == "remember":
            # Already handled via facts
            # Optionally write episodic event here
            pass
            
        elif kind == "reflect" and reply is None:
            # Reflection captured
            reply = "Bridge: Reflection captured."
            logger.info("bridge_route_reply_reflect")
    
    # Record the interpretation as an episodic event
    mem.record_interpretation(safe_text, payload.get("meta", {}))
    
    result = BridgeRouteResult(
        writes=writes,
        tool_calls=tool_calls,
        reply=reply,
        metrics={
            "intents": len(intents),
            "facts": len(facts),
            "patterns": len(payload.get("patterns", [])),
            "tool_calls_made": len(tool_calls),
            "budget_remaining": budget
        },
        discarded=discarded
    )
    
    logger.info("bridge_route_complete", 
               writes=len(writes), 
               tool_calls=len(tool_calls),
               reply_generated=reply is not None)
    
    return result
