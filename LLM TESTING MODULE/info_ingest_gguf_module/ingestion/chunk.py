from typing import List, Dict, Iterable, Optional
from transformers import AutoTokenizer

def token_chunks(text: str, model_name: str = "gpt2", max_tokens: int = 512, overlap: int = 32) -> List[Dict]:
    tok = AutoTokenizer.from_pretrained(model_name)
    if tok.pad_token is None: tok.pad_token = tok.eos_token
    ids = tok.encode(text, add_special_tokens=False)
    chunks = []
    i = 0
    cid = 0
    while i < len(ids):
        window = ids[i:i+max_tokens]
        s = tok.decode(window)
        chunks.append({"chunk_id": cid, "text": s})
        cid += 1
        if i + max_tokens >= len(ids): break
        i += max(1, max_tokens - overlap)
    return chunks