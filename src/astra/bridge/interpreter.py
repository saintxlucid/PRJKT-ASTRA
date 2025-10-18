"""
ASTRA Bridge Interpreter
G-INT pipeline: safety → pattern pass → optional LLM → scoring/prune.
"""
from typing import List, Dict, Any, Callable, Optional
import structlog

from .schemas import BridgeEvent, BridgeIntent, BridgeFact
from .patterns import PATTERNS
from .safety import redact
from .config import BridgeConfig

logger = structlog.get_logger()

# Optional: hook to an LLM (callable) you can inject at runtime
LLM_ABSTRACTOR: Optional[Callable[[str], Dict[str, Any]]] = None


def pattern_pass(text: str) -> Dict[str, Any]:
    """
    Cheap pattern matching against bridge language lexicon.
    Returns dict with matched patterns.
    """
    hits = []
    for pat in PATTERNS:
        if pat.search(text):
            hits.append(pat.pattern)
    
    logger.debug("pattern_pass_complete", pattern_count=len(hits))
    return {"patterns": hits}


def llm_abstraction(text: str) -> Dict[str, Any]:
    """
    Optional LLM-based abstraction into intents and facts.
    Set LLM_ABSTRACTOR at runtime to enable.
    
    Expected LLM output format:
    {
        "intents": [{"kind": "remember|ask|act|reflect", "args": {...}, "confidence": 0.8, "rationale": "..."}],
        "facts": [{"subject": "...", "predicate": "...", "object": "...", "tags": [...], "confidence": 0.9}]
    }
    """
    if LLM_ABSTRACTOR is None:
        logger.debug("llm_abstractor_not_configured")
        return {"intents": [], "facts": []}
    
    try:
        result = LLM_ABSTRACTOR(text)
        logger.info("llm_abstraction_complete", 
                   intent_count=len(result.get("intents", [])),
                   fact_count=len(result.get("facts", [])))
        return result
    except Exception as e:
        logger.error("llm_abstraction_failed", error=str(e))
        return {"intents": [], "facts": []}


def score_and_prune(items: List[Dict[str, Any]], threshold: float) -> List[Dict[str, Any]]:
    """Filter items by confidence threshold."""
    out = []
    for it in items:
        conf = float(it.get("confidence", 0.0))
        if conf >= threshold:
            out.append(it)
    
    logger.debug("score_and_prune", input_count=len(items), output_count=len(out), threshold=threshold)
    return out


def interpret(event: BridgeEvent, cfg: BridgeConfig) -> Dict[str, Any]:
    """
    Main interpretation pipeline:
    1. Safety prefilter (redaction)
    2. Cheap pattern pass
    3. LLM abstraction (optional)
    4. Collect + prune by confidence threshold
    
    Returns:
        {
            "safe_text": str,
            "patterns": List[str],
            "intents": List[Dict],
            "facts": List[Dict],
            "meta": Dict
        }
    """
    logger.info("bridge_interpret_start", source=event.source, channel=event.channel, length=len(event.text))
    
    # 1) Safety prefilter
    safe_text = redact(event.text)
    
    # 2) Cheap pattern pass
    pat = pattern_pass(safe_text)
    
    # 3) LLM abstraction (optional)
    abstr = llm_abstraction(safe_text)
    
    # 4) Collect + prune
    intents = [BridgeIntent(**i).model_dump() for i in abstr.get("intents", [])]
    facts = [BridgeFact(**f).model_dump() for f in abstr.get("facts", [])]
    
    intents = score_and_prune(intents, cfg.interpret_conf_threshold)
    facts = score_and_prune(facts, cfg.interpret_conf_threshold)
    
    result = {
        "safe_text": safe_text,
        "patterns": pat.get("patterns", []),
        "intents": intents,
        "facts": facts,
        "meta": {"ts": event.ts, "request_id": event.request_id}
    }
    
    logger.info("bridge_interpret_complete", 
               pattern_hits=len(result["patterns"]),
               intents=len(intents),
               facts=len(facts))
    
    return result
