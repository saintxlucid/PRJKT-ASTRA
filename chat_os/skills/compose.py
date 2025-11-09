"""Compose skill - Document synthesis using local LLM."""
from __future__ import annotations

from typing import Any

from chat_os.executor import ExecutionContext, register_intent
from chat_os.plan import PlanStep

# Global LLM client (lazy-initialized)
_llm_client = None


def _get_llm_client():
    """
    Get or initialize LLM client singleton.

    Uses LocalLlamaClient from services.llm_service_local with fallback
    to mock responses if model not available.
    """
    global _llm_client

    if _llm_client is not None:
        return _llm_client

    try:
        # Try to import and initialize local LLM service
        import os

        from services.llm_service_local import LLMConfig, LocalLlamaClient

        # Check if model exists (use default or environment variable)
        model_path = os.getenv("ASTRA_LLM_MODEL_PATH", "models/gpt-oss-20b.q5_k_m.gguf")

        if os.path.exists(model_path):
            config = LLMConfig(
                model_path=model_path,
                n_ctx=8192,
                n_threads=8,
                n_gpu_layers=0,  # CPU-only by default
                temperature=0.7,
                max_tokens=2048,
            )
            _llm_client = LocalLlamaClient(config)
            return _llm_client
        else:
            # Model not found - use mock
            print(f"⚠️ LLM model not found at {model_path}, using mock responses")
            _llm_client = "mock"
            return _llm_client

    except Exception as e:
        # Failed to initialize - use mock
        print(f"⚠️ Failed to initialize LLM: {e}, using mock responses")
        _llm_client = "mock"
        return _llm_client


def _call_llm(prompt: str, max_tokens: int = 2048, temperature: float = 0.7) -> str:
    """
    Call local LLM for generation.

    Integrates with services.llm_service_local.LocalLlamaClient.
    Falls back to mock response if LLM not available.
    """
    client = _get_llm_client()

    if client == "mock":
        # Mock response for testing/development
        return f"[Mock LLM Response to: {prompt[:50]}...]"

    try:
        # Call real LLM
        response = client.chat(
            prompt=prompt,
            system="You are ASTRA OS, a local-first AI assistant. Respond concisely and accurately.",
            stop=["<<USER>>", "\n\n\n"],
        )
        return response["text"].strip()

    except Exception as e:
        # Fallback to mock on error
        print(f"⚠️ LLM generation failed: {e}")
        return f"[LLM Error: {str(e)[:100]}]"


@register_intent("compose.document")
def handle_compose_document(step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
    """
    Synthesize a structured document from raw content using LLM.
    
    Args:
        step.args:
            - source: Content to synthesize (string or variable reference)
            - format: Output format (markdown, html, plaintext)
            - style: Writing style (brief, detailed, technical, casual)
            - max_tokens: LLM generation budget
            - temperature: Sampling temperature
    
    Returns:
        Dict with keys: ok, document, format, tokens_used, error
    """
    source = step.args.get("source", "")
    output_format = step.args.get("format", "markdown")
    style = step.args.get("style", "brief")
    max_tokens = int(step.args.get("max_tokens", 1024))
    temperature = float(step.args.get("temperature", 0.7))
    
    if not source:
        return {"ok": False, "error": "Missing required arg: source"}
    
    # Build synthesis prompt
    format_instructions = {
        "markdown": "Use proper markdown formatting with headers, lists, and emphasis.",
        "html": "Generate semantic HTML5 with appropriate tags.",
        "plaintext": "Use plain text with clear paragraph breaks.",
    }
    
    style_instructions = {
        "brief": "Be concise and focus on key points only.",
        "detailed": "Provide comprehensive coverage with examples.",
        "technical": "Use precise terminology and include technical details.",
        "casual": "Use conversational tone and simple language.",
    }
    
    prompt = f"""Synthesize the following raw content into a well-structured document.

Format: {output_format}
Style: {style}

Format Instructions:
{format_instructions.get(output_format, format_instructions["markdown"])}

Style Instructions:
{style_instructions.get(style, style_instructions["brief"])}

Raw Content:
{source}

Structured Document:"""
    
    try:
        # Call LLM
        document = _call_llm(prompt, max_tokens=max_tokens, temperature=temperature)
        
        return {
            "ok": True,
            "document": document,
            "format": output_format,
            "style": style,
            "tokens_used": len(document.split()),  # Rough estimate
        }
    
    except Exception as e:
        return {
            "ok": False,
            "error": f"LLM synthesis failed: {e}",
        }


@register_intent("compose.summarize")
def handle_compose_summarize(step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
    """
    Generate a concise summary of content.
    
    Args:
        step.args:
            - content: Content to summarize
            - max_length: Target summary length (short, medium, long)
            - focus: Optional focus area (key_points, technical, business)
    
    Returns:
        Dict with keys: ok, summary, original_length, summary_length, error
    """
    content = step.args.get("content", "")
    max_length = step.args.get("max_length", "medium")
    focus = step.args.get("focus", "key_points")
    
    if not content:
        return {"ok": False, "error": "Missing required arg: content"}
    
    length_budgets = {
        "short": 150,
        "medium": 300,
        "long": 600,
    }
    
    max_tokens = length_budgets.get(max_length, 300)
    
    prompt = f"""Provide a {max_length} summary of the following content.

Focus: {focus}

Content:
{content}

Summary:"""
    
    try:
        summary = _call_llm(prompt, max_tokens=max_tokens, temperature=0.5)
        
        return {
            "ok": True,
            "summary": summary,
            "original_length": len(content.split()),
            "summary_length": len(summary.split()),
            "compression_ratio": round(len(summary) / len(content), 2),
        }
    
    except Exception as e:
        return {
            "ok": False,
            "error": f"Summarization failed: {e}",
        }


@register_intent("compose.rewrite")
def handle_compose_rewrite(step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
    """
    Rewrite content in a different tone or format.
    
    Args:
        step.args:
            - content: Content to rewrite
            - target_tone: Desired tone (formal, casual, technical, friendly)
            - preserve_facts: Whether to preserve factual content (default: true)
    
    Returns:
        Dict with keys: ok, rewritten, original_tone, target_tone, error
    """
    content = step.args.get("content", "")
    target_tone = step.args.get("target_tone", "professional")
    preserve_facts = step.args.get("preserve_facts", True)
    
    if not content:
        return {"ok": False, "error": "Missing required arg: content"}
    
    fact_instruction = (
        "Preserve all factual information and statistics."
        if preserve_facts
        else "You may adapt facts as needed for the new tone."
    )
    
    prompt = f"""Rewrite the following content in a {target_tone} tone.

{fact_instruction}

Original Content:
{content}

Rewritten Content:"""
    
    try:
        rewritten = _call_llm(prompt, max_tokens=1024, temperature=0.8)
        
        return {
            "ok": True,
            "rewritten": rewritten,
            "target_tone": target_tone,
            "preserve_facts": preserve_facts,
        }
    
    except Exception as e:
        return {
            "ok": False,
            "error": f"Rewrite failed: {e}",
        }
