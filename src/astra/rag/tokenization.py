from __future__ import annotations
from typing import Callable, Optional

try:
    import tiktoken  # optional
except Exception:
    tiktoken = None

def get_token_counter(model_hint: Optional[str] = None) -> Callable[[str], int]:
    """
    Returns a function that counts tokens for a given string.
    Prefers tiktoken if present; otherwise uses a conservative whitespace fallback.
    """
    if tiktoken:
        try:
            # cl100k covers many modern LLMs; adjust via model_hint if you want
            enc = tiktoken.get_encoding("cl100k_base")
            def count(s: str) -> int:
                return len(enc.encode(s or ""))
            return count
        except Exception:
            pass

    def fallback_count(s: str) -> int:
        s = s or ""
        # conservative: whitespace tokens + punctuation bumps
        base = len([w for w in s.split() if w])
        # tiny bump for symbols
        sym = sum(s.count(c) for c in ".,:;!?()[]{}\"'")
        return max(1, base + sym // 8)
    return fallback_count