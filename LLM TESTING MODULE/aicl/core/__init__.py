import json, base64, time, uuid
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any
import hmac, hashlib


def now_iso() -> str:
    """Get current time in ISO format"""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def aicl_core(msg: dict) -> str:
    """Serialize message to AICL-Core JSON format"""
    return json.dumps(msg, separators=(",", ":"), ensure_ascii=False)


def new_msg(frm: str, to: str, act: str, payload: Dict, 
            topic: Optional[str] = None, caps: Optional[List[str]] = None, 
            ctx: Optional[Dict] = None, limits: Optional[Dict] = None) -> Dict:
    """Create a new AICL message"""
    return {
        "v": "aicl/1.0",
        "id": str(uuid.uuid4()),
        "ts": now_iso(),
        "from": frm,
        "to": to,
        "caps": caps or [],
        "act": act,
        "topic": topic or "",
        "ctx": ctx or {},
        "limits": limits or {"tokens": 1024},
        "payload": payload,
        "sig": None
    }


def to_glyph(m: dict) -> str:
    """Convert message to AICL-Glyph compact format"""
    hdr = f"A1|id={m['id']}|f={m['from']}|t={m['to']}|a={m['act']}|tp={m.get('topic', '')}|trn={m.get('ctx', {}).get('turn', 0)}|tk={m.get('limits', {}).get('tokens', 1024)}|"
    lines = [hdr]
    p = m["payload"]
    
    if p.get("text"):
        t = p["text"]
        lines.append(f"TXT:{t.get('lang', 'und')}:{t.get('fmt', 'txt')}|{t.get('content', '')}")
        
    if p.get("emb"):
        e = p["emb"]
        shape_str = 'x'.join(map(str, e['shape']))
        lines.append(f"EMB:{e['model']}:{e['dtype']}:{shape_str}|{e['b64']}")
        
    if p.get("logits"):
        lg = p["logits"]
        pairs = ",".join(f"{x['tok']}={x['p']:.5f}" for x in lg.get("topk", [])[:20])
        lines.append(f"LOG:T={lg.get('temperature', 1.0)}|{pairs}")
        
    if p.get("tool"):
        tl = p["tool"]
        lines.append(f"TL:{tl.get('name')}|{json.dumps(tl.get('args', {}), separators=(',', ':'))}")
        
    return "\n".join(lines)


def from_glyph(s: str) -> dict:
    """Parse AICL-Glyph format back to message dict"""
    lines = s.splitlines()
    parts = {kv.split("=", 1)[0]: kv.split("=", 1)[1] for kv in lines[0].split("|")[1:-1]}
    
    msg = {
        "v": "aicl/1.0",
        "id": parts["id"],
        "ts": now_iso(),
        "from": parts["f"],
        "to": parts["t"],
        "caps": [],
        "act": parts["a"],
        "topic": parts.get("tp", ""),
        "ctx": {"turn": int(parts.get("trn", "0"))},
        "limits": {"tokens": int(parts.get("tk", "1024"))},
        "payload": {},
        "sig": None
    }
    
    for ln in lines[1:]:
        if ln.startswith("TXT:"):
            _, lang, fmt = ln.split("|", 1)[0].split(":")
            content = ln.split("|", 1)[1]
            msg["payload"]["text"] = {"lang": lang, "fmt": fmt, "content": content}
            
        elif ln.startswith("EMB:"):
            head, b64 = ln.split("|", 1)
            _, model, dtype, shape = head.split(":")
            shp = tuple(map(int, shape.split("x")))
            msg["payload"]["emb"] = {"model": model, "dtype": dtype, "shape": shp, "b64": b64}
            
        elif ln.startswith("LOG:"):
            head, body = ln.split("|", 1)
            T = float(head.split("T=")[1])
            topk = []
            for pair in body.split(","):
                if "=" in pair:
                    tok, p = pair.rsplit("=", 1)
                    topk.append({"tok": tok, "p": float(p)})
            msg["payload"]["logits"] = {"temperature": T, "topk": topk}
            
        elif ln.startswith("TL:"):
            name, js = ln[3:].split("|", 1)
            msg["payload"]["tool"] = {"name": name, "args": json.loads(js)}
            
    return msg


def canonical(m: dict) -> bytes:
    """Create canonical representation for signing"""
    tmp = m.copy()
    tmp.pop("sig", None)
    return json.dumps(tmp, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode("utf-8")


def sign(m: dict, key: bytes) -> dict:
    """Sign message with HMAC"""
    m = dict(m)
    m["sig"] = hmac.new(key, canonical(m), hashlib.sha256).hexdigest()
    return m


def verify(m: dict, key: bytes) -> bool:
    """Verify message signature"""
    if not m.get("sig"):
        return False
    expect = hmac.new(key, canonical(m), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expect, m.get("sig", ""))


class AICLBus:
    """Simple message bus for AICL communication"""
    
    def __init__(self):
        self.messages = []
        
    def send(self, msg: dict) -> None:
        """Send a message"""
        self.messages.append(msg)
        
    def receive(self) -> Optional[dict]:
        """Receive a message (FIFO)"""
        if self.messages:
            return self.messages.pop(0)
        return None
        
    def size(self) -> int:
        """Get number of pending messages"""
        return len(self.messages)


# Enhanced message creation functions
def new_stream_msg(frm: str, to: str, topic: str, chunks: List[Dict], 
                   ctx: Optional[Dict] = None) -> Dict:
    """Create a streaming message"""
    return {
        "v": "aicl/1.0",
        "id": f"stream_{uuid.uuid4()}",
        "ts": now_iso(),
        "from": frm,
        "to": to,
        "act": "stream",
        "topic": topic,
        "ctx": ctx or {},
        "limits": {"tokens": 1024},
        "payload": {"chunks": chunks},
        "sig": None
    }


def new_error_msg(frm: str, to: str, error: str, original_msg_id: Optional[str] = None) -> Dict:
    """Create an error message"""
    return {
        "v": "aicl/1.0",
        "id": f"error_{uuid.uuid4()}",
        "ts": now_iso(),
        "from": frm,
        "to": to,
        "act": "error",
        "topic": "",
        "ctx": {"original_msg_id": original_msg_id} if original_msg_id else {},
        "limits": {"tokens": 256},
        "payload": {"error": error},
        "sig": None
    }


def new_ping_msg(frm: str, to: str) -> Dict:
    """Create a ping message"""
    return {
        "v": "aicl/1.0",
        "id": f"ping_{uuid.uuid4()}",
        "ts": now_iso(),
        "from": frm,
        "to": to,
        "act": "ping",
        "topic": "",
        "ctx": {},
        "limits": {"tokens": 64},
        "payload": {},
        "sig": None
    }


def new_pong_msg(frm: str, to: str, ping_id: str) -> Dict:
    """Create a pong message"""
    return {
        "v": "aicl/1.0",
        "id": f"pong_{uuid.uuid4()}",
        "ts": now_iso(),
        "from": frm,
        "to": to,
        "act": "pong",
        "topic": "",
        "ctx": {"ping_id": ping_id},
        "limits": {"tokens": 64},
        "payload": {},
        "sig": None
    }


# Message utility functions
def get_message_type(msg: Dict) -> str:
    """Get the type of message"""
    return msg.get("act", "unknown")


def get_message_topic(msg: Dict) -> str:
    """Get the topic of message"""
    return msg.get("topic", "")


def is_response_message(msg: Dict) -> bool:
    """Check if message is a response"""
    return msg.get("act") in ["answer", "ack", "tool_result", "pong", "error"]


def is_request_message(msg: Dict) -> bool:
    """Check if message is a request"""
    return msg.get("act") in ["ask", "inform", "tool_call", "ping"]


# Example usage functions
def example_handshake():
    """Create example handshake messages"""
    caps = ["text", "emb", "tool:math", "logits:topk"]
    msg1 = new_msg(
        frm="model://neox20b",
        to="model://gpt2l",
        act="inform",
        payload={"caps": caps, "max_ctx": 8192}
    )
    
    msg2 = new_msg(
        frm="model://gpt2l",
        to="model://neox20b",
        act="ack",
        payload={"ok": True}
    )
    
    return msg1, msg2


def example_conversation():
    """Create example conversation messages"""
    # Ask message
    ask = new_msg(
        frm="model://neox20b",
        to="model://gpt2l",
        act="ask",
        ctx={"turn": 1},
        limits={"tokens": 512},
        payload={
            "text": {
                "lang": "en",
                "fmt": "md",
                "content": "Summarize: Large language models are powerful tools for natural language processing tasks."
            }
        }
    )
    
    # Answer message in glyph format
    answer_glyph = """A1|id=abc123|f=model://gpt2l|t=model://neox20b|a=answer|tp=distill|trn=1|tk=512|
TXT:en:md|Here are the key points: 1) LLMs excel at NLP tasks 2) They require significant computational resources"""
    
    return ask, answer_glyph


if __name__ == "__main__":
    # Test the AICL implementation
    print("=== AICL Test ===")
    
    # Create handshake messages
    msg1, msg2 = example_handshake()
    print("Handshake messages:")
    print(aicl_core(msg1))
    print(aicl_core(msg2))
    
    # Create conversation messages
    ask, answer_glyph = example_conversation()
    print("\nAsk message (Core JSON):")
    print(aicl_core(ask))
    
    print("\nAnswer message (Glyph):")
    print(answer_glyph)
    
    # Parse glyph back to dict
    parsed_answer = from_glyph(answer_glyph)
    print("\nParsed answer (back to Core):")
    print(aicl_core(parsed_answer))
    
    # Test signing
    key = b"test_key"
    signed_msg = sign(msg1, key)
    print("\nSigned message verification:", verify(signed_msg, key))