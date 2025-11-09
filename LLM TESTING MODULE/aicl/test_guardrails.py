import guardrails

# Test message validation
valid_msg = {
    "v": "aicl/1.0",
    "id": "test12345678",  # Longer ID to pass validation
    "from": "sender",
    "to": "receiver",
    "act": "inform",
    "payload": {"test": "data"}
}

print("Testing message validation...")
is_valid, error = guardrails.validate_message(valid_msg)
print(f"Valid message: {is_valid}, Error: {error}")

# Test invalid message
invalid_msg = {
    "v": "aicl/1.0",
    "id": "test12345678",
    "from": "sender",
    "to": "receiver",
    "act": "invalid_act",  # Invalid act
    "payload": {"test": "data"}
}

is_valid, error = guardrails.validate_message(invalid_msg)
print(f"Invalid message: {is_valid}, Error: {error}")

# Test rate limiting
print("\nTesting rate limiting...")
sender_id = "test_sender"
for i in range(5):
    allowed = guardrails.rate_limit_check(sender_id, max_requests_per_minute=10)
    print(f"Request {i+1}: Allowed = {allowed}")

# Test signature verification
print("\nTesting signature verification...")
key = b"test_key"
signed_msg = valid_msg.copy()
signed_msg["sig"] = "dummy_signature"
is_verified = guardrails.verify_signature(signed_msg, key)
print(f"Signature verification: {is_verified}")

print("\nAll guardrail tests completed!")