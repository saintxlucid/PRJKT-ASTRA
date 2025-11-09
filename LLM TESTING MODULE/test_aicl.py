import sys
import os

# Add the aicl directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'aicl'))

try:
    # Test importing the core module directly
    import aicl.core
    print("✓ Core module imported successfully")
    
    # Test creating a message
    msg = aicl.core.new_msg(
        frm="test_sender",
        to="test_receiver",
        act="inform",
        payload={"test": "data"}
    )
    print("✓ Message creation successful")
    print(f"Message: {aicl.core.aicl_core(msg)}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()