# Test Harmony parsing
from astra.infrastructure.llm.harmony import parse_harmony_response, extract_final_response

raw = """We need to respond with just "I am working correctly." per the user request. No other text.
But check: Are there any instructions to refuse? The user wants a simple statement. It's allowed. So we should respond exactly: "I am working correctly." with no extra punctuation? The user says "Just: I am working correctly." So we need to output that phrase exactly, perhaps including a period at the end? The phrase includes a period? The phrase "I am working correctly." includes a period. The user says "Just: I am working correctly." That includes a period. So we should output: "I am working correctly." Yes. No other text.
Let's comply.<|end|><|start|>assistant<|channel|>final<|message|>I am working correctly."""

print("Raw response:")
print(raw)
print("\n" + "="*60)

parsed = parse_harmony_response(raw)
print(f"\nParsed {len(parsed)} messages:")
for i, msg in enumerate(parsed):
    print(f"\n{i+1}. Role: {msg.role}, Channel: {msg.channel}")
    print(f"   Content: {msg.content[:100]}...")

print("\n" + "="*60)
final = extract_final_response(parsed)
print(f"\nExtracted final response:")
print(final)
