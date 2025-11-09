import core

# Test basic functionality
msg = core.new_msg(
    frm="test_sender",
    to="test_receiver",
    act="inform",
    payload={"test": "data"}
)

print("Message created successfully")
print(core.aicl_core(msg))

# Test signing
signed = core.sign(msg, b"test_key")
print("Message signed successfully")

# Test verification
is_valid = core.verify(signed, b"test_key")
print(f"Signature valid: {is_valid}")

print("All tests passed!")