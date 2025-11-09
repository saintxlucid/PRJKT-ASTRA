"""
ASTRA 2.0 Base Model Body Service
Base class for specialized model bodies (Creative, Code, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import asyncio
import httpx
import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os

logger = structlog.get_logger("astra.model_body")

class GenerationRequest(BaseModel):
    """Request for model generation"""
    prompt: str
    max_tokens: int = 1000
    temperature: float = 0.7
    stop_sequences: List[str] = []
    context: Optional[Dict[str, Any]] = None

class GenerationResponse(BaseModel):
    """Response from model generation"""
    text: str
    usage: Dict[str, int]
    model_id: str
    metadata: Dict[str, Any]

class ModelBody(ABC):
    """Base class for ASTRA model bodies"""
    
    def __init__(
        self,
        name: str,
        model_id: str,
        orchestrator_url: str,
        use_cases: List[str],
        constraints: Dict[str, Any]
    ):
        self.name = name
        self.model_id = model_id
        self.orchestrator_url = orchestrator_url
        self.use_cases = use_cases
        self.constraints = constraints
        self._http_client = httpx.AsyncClient()
        
    async def register_with_orchestrator(self):
        """Register this body with the orchestrator"""
        try:
            response = await self._http_client.post(
                f"{self.orchestrator_url}/register_body",
                json={
                    "name": self.name,
                    "model_id": self.model_id,
                    "use_cases": self.use_cases,
                    "constraints": self.constraints,
                    "api_url": f"http://localhost:{os.environ.get('PORT', 8000)}"
                }
            )
            response.raise_for_status()
            logger.info(f"Registered {self.name} with orchestrator")
            
        except Exception as e:
            logger.error(f"Failed to register with orchestrator: {e}")
            raise
            
    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text from the model"""
        pass
    
    @abstractmethod
    async def load_model(self):
        """Load the model into memory"""
        pass
    
    async def verify_response(self, response: str) -> bool:
        """Verify response with soul core"""
        try:
            async with httpx.AsyncClient() as client:
                result = await client.post(
                    "http://soul_core:8001/verify_response",
                    json={"response": response}
                )
                return result.json()["approved"]
        except Exception as e:
            logger.error(f"Failed to verify response: {e}")
            return False

# FastAPI app template
def create_app(body: ModelBody) -> FastAPI:
    """Create FastAPI app for a model body"""
    app = FastAPI(title=f"ASTRA {body.name} Service")
    
    @app.on_event("startup")
    async def startup():
        await body.load_model()
        await body.register_with_orchestrator()
    
    @app.post("/generate")
    async def generate(request: GenerationRequest) -> GenerationResponse:
        return await body.generate(request)
    
    return app