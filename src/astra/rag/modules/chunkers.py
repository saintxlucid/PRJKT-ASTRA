"""
Chunkers: sliding, semantic, recursive, code-aware, adaptive
All return List[str] of text chunks ready for embedding/indexing.
"""
import re
from typing import List


def sliding(text: str, size: int = 900, overlap: int = 128) -> List[str]:
    """Fixed-size sliding window with overlap."""
    out, i, n = [], 0, len(text)
    step = max(size - overlap, 1)
    while i < n:
        j = min(i + size, n)
        chunk = text[i:j].strip()
        if chunk:
            out.append(chunk)
        if j >= n:
            break
        i += step
    return out


def semantic(text: str, min_len: int = 400, max_len: int = 900) -> List[str]:
    """Split on blank lines (paragraphs) respecting min/max bounds."""
    blocks = re.split(r"\n\s*\n+", text)  # blank line separates paragraphs
    chunks, cur = [], ""
    for block in blocks:
        if len(cur) + len(block) < max_len:
            cur = (cur + "\n\n" + block).strip()
        else:
            if len(cur) >= min_len:
                chunks.append(cur)
            cur = block
    if cur and len(cur) >= min_len:
        chunks.append(cur)
    return chunks or [text[:max_len]]


def recursive(text: str, max_len: int = 900, min_len: int = 200, overlap: int = 64) -> List[str]:
    """Recursive splitting: try paragraphs, then sentences, fallback to sliding."""
    if len(text) <= max_len:
        return [text]
    
    # Try paragraphs
    paras = re.split(r"\n\s*\n+", text)
    if len("".join(paras[:1])) > max_len:
        # Paragraphs too large, split by sentences
        sents = re.split(r"(?<=[.!?])\s+", text)
        chunks, cur = [], ""
        for sent in sents:
            if len(cur) + len(sent) <= max_len:
                cur += (sent + " ")
            else:
                if len(cur) >= min_len:
                    chunks.append(cur.strip())
                cur = sent + " "
        if cur:
            chunks.append(cur.strip())
        if not chunks:
            return sliding(text, size=max_len, overlap=overlap)
        return chunks
    else:
        # Paragraphs fit, use semantic
        return semantic(text, min_len=min_len, max_len=max_len)


def code_aware(text: str, size: int = 1000, min_chunk: int = 256) -> List[str]:
    """Split by function/class definitions and docstrings."""
    parts = re.split(r"(?m)^\s*(def |class |###|''\'\'\'|\"\"\")", text)
    if len(parts) <= 1:
        return sliding(text, size=size, overlap=128)
    
    chunks, cur = [], ""
    for part in parts:
        cur += part
        if len(cur) >= min_chunk:
            chunks.append(cur.strip())
            cur = ""
    if cur:
        chunks.append(cur.strip())
    
    return [c for c in chunks if c]


def adaptive(text: str, hint: str = "default") -> List[str]:
    """Adaptive: shrink for code, grow for prose."""
    if re.search(r"[{}/();:=]", text):  # code-ish
        return code_aware(text)
    if len(text) > 2000:
        return recursive(text, max_len=900, min_len=250)
    return semantic(text, min_len=300, max_len=800)
