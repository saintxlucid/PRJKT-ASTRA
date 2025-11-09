"""
ASTRA Core LLM Interface - GPT-OSS Integration Layer
"""
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import asyncio
from dataclasses import dataclass
from enum import Enum

import torch
from llama_cpp import Llama
from transformers import AutoTokenizer, AutoModelForCausalLM

from ..memory.vector_store import VectorStore
from ...security.activity_audit import audit_action

class ModelType(Enum):
    GGUF = "gguf"  # Quantized GGUF format
    PYTORCH = "pytorch"  # Full PyTorch model
    
@dataclass
class ModelConfig:
    model_type: ModelType
    model_path: Path
    context_size: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    
class ASTRACore:
    """Core LLM interface for ASTRA's cognitive system"""
    
    def __init__(self, config: ModelConfig, vector_store: VectorStore):
        self.config = config
        self.vector_store = vector_store
        self._load_model()
        
    def _load_model(self) -> None:
        """Load the core LLM model"""
        if self.config.model_type == ModelType.GGUF:
            self.model = Llama(
                model_path=str(self.config.model_path),
                n_ctx=self.config.context_size,
                n_threads=8,
                n_batch=512
            )
            audit_action("model.load", {
                "type": "gguf",
                "path": str(self.config.model_path)
            })
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(self.config.model_path)
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                str(self.config.model_path),
                torch_dtype=torch.float16,
                device_map="auto"
            )
            audit_action("model.load", {
                "type": "pytorch",
                "path": str(self.config.model_path)
            })
            
    async def generate(self, 
                      prompt: str,
                      system_prompt: Optional[str] = None,
                      memory_context: Optional[List[Dict]] = None,
                      tools_context: Optional[List[Dict]] = None,
                      **kwargs) -> str:
        """Generate response with full context integration"""
        
        # Build context window
        context_parts = []
        
        if system_prompt:
            context_parts.append(f"[SYSTEM]\n{system_prompt}\n")
            
        if memory_context:
            memories = "\n".join(
                f"[MEMORY] {m['content']} ({m['type']})" 
                for m in memory_context
            )
            context_parts.append(f"[MEMORIES]\n{memories}\n")
            
        if tools_context:
            tools = json.dumps(tools_context, indent=2)
            context_parts.append(f"[TOOLS]\n{tools}\n")
            
        context_parts.append(f"[USER]\n{prompt}\n[ASSISTANT]\n")
        full_prompt = "\n".join(context_parts)
        
        # Generate with appropriate backend
        if self.config.model_type == ModelType.GGUF:
            response = self.model(
                full_prompt,
                max_tokens=kwargs.get("max_tokens", 1024),
                temperature=kwargs.get("temperature", self.config.temperature),
                top_p=kwargs.get("top_p", self.config.top_p),
                top_k=kwargs.get("top_k", self.config.top_k),
                presence_penalty=kwargs.get(
                    "presence_penalty", 
                    self.config.presence_penalty
                ),
                frequency_penalty=kwargs.get(
                    "frequency_penalty", 
                    self.config.frequency_penalty
                ),
                stop=["[USER]", "[SYSTEM]"]
            )
            generated_text = response["choices"][0]["text"]
        else:
            inputs = self.tokenizer(
                full_prompt, 
                return_tensors="pt",
                truncation=True,
                max_length=self.config.context_size
            ).to(self.model.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=kwargs.get("max_tokens", 1024),
                    temperature=kwargs.get("temperature", self.config.temperature),
                    top_p=kwargs.get("top_p", self.config.top_p),
                    top_k=kwargs.get("top_k", self.config.top_k),
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
                
            generated_text = self.tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[-1]:],
                skip_special_tokens=True
            )
            
        audit_action("model.generate", {
            "prompt_length": len(prompt),
            "response_length": len(generated_text)
        })
        
        return generated_text.strip()
        
    async def generate_with_tools(self,
                                prompt: str,
                                available_tools: List[Dict],
                                **kwargs) -> Dict[str, Any]:
        """Generate response with tool usage capabilities"""
        
        tools_context = json.dumps({
            "available_tools": available_tools,
            "format": "You can use tools by outputting: "
                     "{{\"tool\": \"tool_name\", \"args\": {\"arg1\": \"value\"}}}"
        })
        
        response = await self.generate(
            prompt,
            tools_context=available_tools,
            **kwargs
        )
        
        # Parse potential tool calls
        try:
            tool_call = json.loads(response)
            if "tool" in tool_call and "args" in tool_call:
                return {
                    "type": "tool_call",
                    "tool": tool_call["tool"],
                    "args": tool_call["args"]
                }
        except json.JSONDecodeError:
            pass
            
        return {
            "type": "text",
            "content": response
        }
        
    def update_memory(self, text: str, metadata: Dict) -> None:
        """Update vector memory with new content"""
        self.vector_store.add_texts([text], [metadata])
        
    async def search_memory(self, 
                          query: str, 
                          limit: int = 5) -> List[Dict]:
        """Search vector memory for relevant context"""
        results = self.vector_store.similarity_search(query, k=limit)
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            }
            for doc, score in results
        ]