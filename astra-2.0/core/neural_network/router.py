"""
ASTRA Neural Router - Multi-Model Orchestration
"""
from typing import Dict, List, Optional, Any
import asyncio
from enum import Enum
from dataclasses import dataclass
import json

from .llm.astra_core import ASTRACore
from ..security.activity_audit import audit_action

class Domain(Enum):
    GENERAL = "general"  # Default ASTRA Core
    MUSIC = "music"      # Music generation/analysis
    VISION = "vision"    # Image/video processing
    CODE = "code"        # Code generation/analysis
    SECURITY = "security"  # Security analysis
    
@dataclass
class ModelEndpoint:
    domain: Domain
    url: str
    api_key: Optional[str] = None
    
class NeuralRouter:
    """Routes requests to appropriate sub-LLMs based on domain"""
    
    def __init__(self, core: ASTRACore):
        self.core = core
        self.endpoints: Dict[Domain, ModelEndpoint] = {}
        
    def register_endpoint(self, endpoint: ModelEndpoint) -> None:
        """Register a new sub-LLM endpoint"""
        self.endpoints[endpoint.domain] = endpoint
        audit_action("router.register", {
            "domain": endpoint.domain.value,
            "url": endpoint.url
        })
        
    async def _call_submodel(self,
                            endpoint: ModelEndpoint,
                            prompt: str,
                            **kwargs) -> Dict:
        """Call a sub-LLM endpoint"""
        # Implement actual API calls here
        # This is a placeholder that returns to core model
        return await self.core.generate(
            f"[{endpoint.domain.value.upper()}]\n{prompt}",
            **kwargs
        )
        
    async def route_request(self,
                          prompt: str,
                          domain_hints: Optional[List[Domain]] = None,
                          **kwargs) -> Dict[str, Any]:
        """Route request to appropriate model(s)"""
        
        # If no hints, ask core to analyze
        if not domain_hints:
            analysis = await self.core.generate(
                f"Analyze this request and output JSON with domains "
                f"from {[d.value for d in Domain]}: {prompt}",
                max_tokens=100
            )
            try:
                domain_hints = [
                    Domain(d) for d in json.loads(analysis).get("domains", [])
                ]
            except (json.JSONDecodeError, ValueError):
                domain_hints = [Domain.GENERAL]
                
        audit_action("router.route", {
            "domains": [d.value for d in domain_hints],
            "prompt_length": len(prompt)
        })
        
        # Handle single domain
        if len(domain_hints) == 1:
            domain = domain_hints[0]
            if domain == Domain.GENERAL or domain not in self.endpoints:
                return {
                    "domain": domain.value,
                    "response": await self.core.generate(prompt, **kwargs)
                }
            else:
                return {
                    "domain": domain.value,
                    "response": await self._call_submodel(
                        self.endpoints[domain],
                        prompt,
                        **kwargs
                    )
                }
                
        # Handle multi-domain
        tasks = []
        for domain in domain_hints:
            if domain == Domain.GENERAL or domain not in self.endpoints:
                tasks.append(self.core.generate(prompt, **kwargs))
            else:
                tasks.append(
                    self._call_submodel(
                        self.endpoints[domain],
                        prompt,
                        **kwargs
                    )
                )
                
        responses = await asyncio.gather(*tasks)
        
        # Merge responses (placeholder - implement sophisticated fusion)
        return {
            "domains": [d.value for d in domain_hints],
            "responses": responses
        }
        
    async def route_tool_request(self,
                               prompt: str,
                               tools: List[Dict],
                               domain_hints: Optional[List[Domain]] = None,
                               **kwargs) -> Dict[str, Any]:
        """Route tool-using request to appropriate model"""
        
        # Tool requests always go through core first
        core_response = await self.core.generate_with_tools(
            prompt, tools, **kwargs
        )
        
        # If core wants to use a tool, do that
        if core_response["type"] == "tool_call":
            return core_response
            
        # Otherwise, try sub-models if we have domain hints
        if domain_hints:
            return await self.route_request(prompt, domain_hints, **kwargs)
            
        return core_response