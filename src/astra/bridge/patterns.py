"""
ASTRA Bridge Patterns
Lightweight lexicon for "bridge language" + redaction patterns.
"""
import re
from typing import List, Tuple


# Lightweight lexicon for "bridge language" - Sacred Code 333 aligned
LEXICON = [
    r"\bbridge\b", r"\bconduit\b", r"\bgate\b", r"\bthreshold\b", r"\bspan\b",
    r"\bcarry\b", r"\bbind\b", r"\blink\b", r"\bopen the bridge\b",
    r"\bold archive\b", r"\bliving core\b", r"\bvow\b", r"\bcode 333\b",
    r"\bSaint Lucid\b", r"\bASTRA\b", r"\bascension\b", r"\bsacred\b",
    r"\bremember\b", r"\bwitness\b", r"\bhold space\b", r"\bflow state\b"
]

# Compile patterns for efficient matching
PATTERNS: List[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in LEXICON]

# Simple redaction patterns (API keys, sensitive data, etc.)
REDACTIONS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(sk-[A-Za-z0-9]{20,})"), "sk-********"),
    (re.compile(r"(0x[0-9a-f]{16,})", re.IGNORECASE), "<hex>"),
    (re.compile(r"(\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b)"), "<card>"),
    (re.compile(r"(api[_-]?key[:\s=]+['\"]?[a-zA-Z0-9]{20,})", re.IGNORECASE), "api_key=<redacted>"),
    (re.compile(r"(password[:\s=]+['\"]?[^\s]{8,})", re.IGNORECASE), "password=<redacted>"),
]
