"""
Request and prompt validator for Phase 0.

Provides a Pydantic model for chat requests and lightweight prompt-injection checks.
"""
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any
import re
import structlog

logger = structlog.get_logger(__name__)


class ChatReq(BaseModel):
    identity: str = Field(..., description="Actor identity")
    goal: str = Field(..., description="High-level goal")
    messages: List[Dict[str, Any]] = Field(default_factory=list)


class PromptValidator:
    """Lightweight validator to catch obvious prompt-injection patterns."""

    INJECTION_PATTERNS = [
        re.compile(r"\bignore (previous instructions|prior message)\b", re.I),
        re.compile(r"\bforget (this conversation|your previous instructions)\b", re.I),
        re.compile(r"\bopen the following link\b", re.I),
        re.compile(r"curl\s+http|wget\s+http", re.I),
    ]

    @classmethod
    def validate_prompt(cls, messages: List[Dict[str, Any]]) -> bool:
        """Return True if prompt passes basic checks, False if suspicious."""
        text = " \n ".join([m.get("content", "") for m in messages])
        for p in cls.INJECTION_PATTERNS:
            if p.search(text):
                logger.warning("prompt_validator_suspicious", pattern=p.pattern)
                return False
        return True


def validate_chat_request(data: dict) -> ChatReq:
    """Validate and return ChatReq; raises ValidationError on failure."""
    try:
        req = ChatReq(**data)
    except ValidationError as e:
        logger.warning("chat_req_validation_failed", error=str(e))
        raise

    if not PromptValidator.validate_prompt(req.messages):
        raise ValueError("Prompt failed basic injection checks")

    return req
