import re
from typing import List

WHITESPACE_RE = re.compile(r"[\t\f\r]+")
MULTI_NEWLINES_RE = re.compile(r"\n{3,}")
DASHES_RE = re.compile(r"[\u2012-\u2015]+")

def normalize(text: str) -> str:
    t = text.replace("\u00a0", " ")
    t = WHITESPACE_RE.sub(" ", t)
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = MULTI_NEWLINES_RE.sub("\n\n", t)
    t = DASHES_RE.sub("-", t)
    return t.strip()

def strip_boilerplate(lines: List[str]) -> str:
    # Simple heuristic boilerplate remover (headers/footers across pages)
    if not lines: return ""
    # Drop lines that repeat frequently
    freq = {}
    for ln in lines:
        k = ln.strip()
        if not k: continue
        freq[k] = freq.get(k, 0) + 1
    keep = []
    for ln in lines:
        k = ln.strip()
        if not k: 
            keep.append("")
            continue
        if freq.get(k, 0) > max(3, len(lines)//10):
            keep.append("")
        else:
            keep.append(ln)
    return normalize("\n".join(keep))