"""
Response templates for consistent output formatting.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)

# Default prompt templates
SYSTEM_TEMPLATE = """SYSTEM:
You are an AI assistant with access to relevant context.
Use only information from provided memories.
Always cite your sources using [src#] markers.
Keep responses clear and concise.
{system_context}
"""

PERSONA_TEMPLATE = """PERSONA:
{persona_description}
"""

MEMORY_TEMPLATE = """MEMORY:
{memory_text}
"""

USER_TEMPLATE = """USER:
{user_query}
"""

@dataclass
class Citation:
    """Represents a citation in a response."""
    id: str
    source: str
    text: str
    energy: float
    timestamp: Optional[str] = None

class ResponseTemplate:
    """Template manager for responses."""
    
    def __init__(self):
        """Initialize templates."""
        self.system_template = SYSTEM_TEMPLATE
        self.persona_template = PERSONA_TEMPLATE
        self.memory_template = MEMORY_TEMPLATE
        self.user_template = USER_TEMPLATE
        
    def format_prompt(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        system_context: Optional[str] = None,
        persona: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Format prompt with templates.
        
        Args:
            query: User query
            memories: Retrieved memory data
            system_context: Optional system context
            persona: Optional persona data
            
        Returns:
            Formatted prompt string
        """
        blocks = []
        
        # System
        if system_context:
            blocks.append(
                self.system_template.format(
                    system_context=system_context
                )
            )
            
        # Persona 
        if persona:
            blocks.append(
                self.persona_template.format(
                    persona_description=persona.get("description", "")
                )
            )
            
        # Memories
        for i, mem in enumerate(memories, 1):
            blocks.append(
                self.memory_template.format(
                    memory_text=f"[src{i}] {mem['text']}"
                )
            )
            
        # User query
        blocks.append(
            self.user_template.format(
                user_query=query
            )
        )
        
        return "\n\n".join(blocks)
        
    def format_response(
        self,
        response_text: str,
        citations: List[Dict[str, Any]],
        trace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Format response with metadata.
        
        Args:
            response_text: Generated response text
            citations: Citation data
            trace_id: Optional trace identifier
            metadata: Optional response metadata
            
        Returns:
            Formatted response object
        """
        formatted_citations = []
        
        # Process citations
        for i, cite in enumerate(citations, 1):
            formatted_citations.append(
                Citation(
                    id=cite.get("id", f"src{i}"),
                    source=cite.get("source", "unknown"),
                    text=cite.get("text", ""),
                    energy=cite.get("energy", 0.0),
                    timestamp=cite.get("timestamp")
                ).__dict__
            )
            
        return {
            "response": response_text,
            "citations": formatted_citations,
            "trace_id": trace_id,
            "metadata": metadata or {}
        }
        
    def set_system_template(self, template: str) -> None:
        """Set custom system template."""
        self.system_template = template
        
    def set_persona_template(self, template: str) -> None:
        """Set custom persona template."""
        self.persona_template = template
        
    def set_memory_template(self, template: str) -> None:
        """Set custom memory template."""
        self.memory_template = template
        
    def set_user_template(self, template: str) -> None:
        """Set custom user template."""
        self.user_template = template