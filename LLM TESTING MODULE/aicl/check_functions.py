import core

# Check what functions are available
functions = [attr for attr in dir(core) if not attr.startswith('_')]
print("Available functions:")
for func in functions:
    print(f"  {func}")

# Test specific functions
print("\nTesting specific functions:")
print(f"AICLBus: {'AICLBus' in functions}")
print(f"new_msg: {'new_msg' in functions}")
print(f"aicl_core: {'aicl_core' in functions}")
print(f"to_glyph: {'to_glyph' in functions}")
print(f"from_glyph: {'from_glyph' in functions}")
print(f"sign: {'sign' in functions}")
print(f"verify: {'verify' in functions}")