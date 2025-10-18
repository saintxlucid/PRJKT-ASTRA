"""
ASTRA Chat Template and Token Management
Manages chat templates and special tokens for ASTRA's LLM interface.
Created: October 16, 2025
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from jinja2 import Template
import structlog

logger = structlog.get_logger()

# ASTRA special tokens
ASTRA_TOKENS = [
    "<|astra.plan|>",
    "<|astra.steps|>",
    "<|astra.tool_call|>",
    "<|astra.tool_result|>",
    "<|astra.consent.explicit|>",
    "<|astra.consent.explicit_with_backup|>",
    "<|astra.backup.injected|>",
    "<|astra.verify.pass|>",
    "<|astra.verify.fail|>",
    "<|astra.rationale|>",
    "<|astra.end|>"
]

# Default chat template
DEFAULT_TEMPLATE = """{% if messages[0]['role'] != 'system' %}
{{- '<|system|> You are ASTRA, a values-aligned operator-first assistant.' -}}
{% endif %}
{%- for m in messages %}
{%- if m['role'] == 'system' -%}
<|system|> {{ m['content'] }}
{%- elif m['role'] == 'user' -%}
<|user|> {{ m['content'] }}
{%- elif m['role'] == 'assistant' -%}
<|assistant|> {{ m['content'] }}
{%- elif m['role'] == 'tool' -%}
<|astra.tool_result|> {{ m['content'] }} <|astra.end|>
{%- endif -%}
{%- endfor %}"""

class ChatManager:
    """Manages chat templating and token handling"""
    
    def __init__(self, template: Optional[str] = None):
        """
        Initialize chat manager
        Args:
            template: Optional custom chat template
        """
        self.template = Template(template or DEFAULT_TEMPLATE)
        self.special_tokens = set(ASTRA_TOKENS)
        
        logger.info("Initialized chat manager")
    
    def format_messages(
        self,
        messages: List[Dict[str, str]],
        plan_mode: bool = False
    ) -> str:
        """
        Format messages using chat template
        Args:
            messages: List of message dictionaries
            plan_mode: Whether to append plan marker
        Returns:
            Formatted chat string
        """
        formatted = self.template.render(messages=messages)
        if plan_mode:
            formatted += "\n<|assistant|> <|astra.plan|>"
        return formatted
    
    def export_tokens(self, path: Path) -> None:
        """
        Export special tokens to JSON file
        Args:
            path: Output path for tokens.json
        """
        with open(path, 'w') as f:
            json.dump({
                "additional_special_tokens": list(self.special_tokens)
            }, f, indent=2)
        
        logger.info(
            "Exported special tokens",
            path=str(path),
            count=len(self.special_tokens)
        )
    
    def export_template(self, path: Path) -> None:
        """
        Export chat template to file
        Args:
            path: Output path for template file
        """
        with open(path, 'w') as f:
            f.write(self.template.source)
        
        logger.info(
            "Exported chat template",
            path=str(path)
        )
    
    def validate_message(self, message: Dict[str, str]) -> bool:
        """
        Validate message format
        Args:
            message: Message dictionary
        Returns:
            True if valid
        """
        required_keys = {'role', 'content'}
        valid_roles = {'system', 'user', 'assistant', 'tool'}
        
        return (
            all(key in message for key in required_keys) and
            message['role'] in valid_roles and
            isinstance(message['content'], str)
        )
    
    def extract_plan(self, response: str) -> Optional[str]:
        """
        Extract plan JSON from response
        Args:
            response: Model response string
        Returns:
            Plan JSON string if found, else None
        """
        start = "<|astra.plan|>"
        end = "<|astra.end|>"
        
        if start in response and end in response:
            plan = response[
                response.index(start) + len(start):
                response.index(end)
            ].strip()
            return plan
        
        return None
    
    def extract_rationale(self, response: str) -> Optional[str]:
        """
        Extract alignment rationale from response
        Args:
            response: Model response string
        Returns:
            Rationale string if found, else None
        """
        start = "<|astra.rationale|>"
        end = "<|astra.end|>"
        
        if start in response and end in response:
            rationale = response[
                response.index(start) + len(start):
                response.index(end)
            ].strip()
            return rationale
        
        return None