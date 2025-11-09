"""
ASTRA Whisper Wake Phrase Configuration
Defines recognized wake phrases for voice activation
"""

from typing import List
from astra.core.activation.prime_request import WAKE_PHRASES

def get_wake_phrases() -> List[str]:
    """Get the list of valid wake phrases for Whisper"""
    return WAKE_PHRASES

def is_wake_phrase(text: str) -> bool:
    """Check if text contains a valid wake phrase"""
    return any(wake.lower() in text.lower() for wake in WAKE_PHRASES)