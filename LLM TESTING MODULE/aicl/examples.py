# AICL Usage Examples
#
# This script demonstrates various AICL communication patterns between LLMs.

from core import (
    AICLBus,
    new_msg,
    aicl_core,
    to_glyph,
    from_glyph,
    sign,
    verify
)

# Initialize message bus
bus = AICLBus()

# 1. Handshake - Capability negotiation
print("=== Handshake ===")
caps = ["text", "emb", "tool:math", "logits:topk"]

# Teacher model introduces itself
teacher_intro = new_msg(
    frm="model://neox20b",
    to="model://gpt2l",
    act="inform",
    payload={
        "caps": caps,
        "max_ctx": 8192
    }
)
print("Teacher capabilities:", aicl_core(teacher_intro))

# Student model acknowledges
student_ack = new_msg(
    frm="model://gpt2l",
    to="model://neox20b",
    act="ack",
    payload={"ok": True}
)
print("Student ack:", aicl_core(student_ack))

# 2. Knowledge Distillation Exchange
print("\n=== Knowledge Distillation ===")

# Teacher asks student to summarize
ask_summary = new_msg(
    frm="model://neox20b",
    to="model://gpt2l",
    act="ask",
    topic="distillation",
    ctx={"turn": 1},
    limits={"tokens": 512},
    payload={
        "text": {
            "lang": "en",
            "fmt": "md",
            "content": "Summarize this technical paper on knowledge distillation:\n\nKnowledge distillation is a technique where a smaller 'student' model is trained to replicate the behavior of a larger 'teacher' model..."
        }
    }
)
print("Teacher asks:", aicl_core(ask_summary))

# Student responds with summary (in compact glyph format for efficiency)
summary_response = """A1|id=sum123|f=model://gpt2l|t=model://neox20b|a=answer|tp=distill|trn=1|tk=256|
TXT:en:md|Knowledge distillation enables efficient model compression by training smaller student models to mimic larger teacher models. Key benefits include reduced computational requirements while maintaining performance."""
print("Student responds (glyph):")
print(summary_response)

# Parse the glyph response
parsed_response = from_glyph(summary_response)
print("Parsed response:", aicl_core(parsed_response))

# 3. Logits Transfer for Distillation
print("\n=== Logits Transfer ===")

# Teacher sends top-k logits for a specific token position
logits_msg = new_msg(
    frm="model://neox20b",
    to="model://gpt2l",
    act="inform",
    topic="logits",
    payload={
        "logits": {
            "temperature": 2.0,
            "topk": [
                {"tok": "distillation", "p": 0.35},
                {"tok": "compression", "p": 0.25},
                {"tok": "transfer", "p": 0.15},
                {"tok": "learning", "p": 0.12},
                {"tok": "model", "p": 0.10}
            ]
        }
    }
)
print("Teacher logits:", aicl_core(logits_msg))

# Convert to glyph for token efficiency
logits_glyph = to_glyph(logits_msg)
print("Logits in glyph format:")
print(logits_glyph)

# 4. Tool Usage
print("\n=== Tool Usage ===")

# Teacher requests math computation
math_request = new_msg(
    frm="model://neox20b",
    to="model://gpt2l",
    act="tool_call",
    payload={
        "tool": {
            "name": "math.evaluate",
            "args": {
                "expr": "softmax([2.1, 1.8, 0.9])"
            }
        }
    }
)
print("Tool call:", aicl_core(math_request))

# Student returns result
math_result = new_msg(
    frm="model://gpt2l",
    to="model://neox20b",
    act="tool_result",
    payload={
        "tool": {
            "name": "math.evaluate",
            "ok": True,
            "result": "[0.52, 0.39, 0.09]"
        }
    }
)
print("Tool result:", aicl_core(math_result))

# 5. Secure Communication with Signing
print("\n=== Secure Communication ===")

# Sign a message
secret_key = b"distillation_key"
signed_msg = sign(ask_summary, secret_key)
print("Signed message:", aicl_core(signed_msg))

# Verify signature
is_valid = verify(signed_msg, secret_key)
print("Signature valid:", is_valid)

# 6. Message Bus Usage
print("\n=== Message Bus ===")

# Send messages through bus
bus.send(teacher_intro)
bus.send(ask_summary)
bus.send(logits_msg)

print(f"Messages in bus: {bus.size()}")

# Receive messages
while bus.size() > 0:
    msg = bus.receive()
    if msg is not None:
        print(f"Received: {msg['act']} from {msg['from']}")