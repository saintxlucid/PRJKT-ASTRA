#!/usr/bin/env python3
"""
Test script to verify all AICL modules can be imported correctly
"""

print("Testing AICL module imports...")

try:
    # Test core module
    from aicl.core import (
        new_msg, 
        aicl_core, 
        to_glyph, 
        from_glyph, 
        sign, 
        verify
    )
    print("✓ Core module imports successful")
    
    # Test transport module
    from aicl.transport import run_server, run_client
    print("✓ Transport module imports successful")
    
    # Test logging module
    from aicl.aicl_logging import AICLLogger, AICLReplayer
    print("✓ Logging module imports successful")
    
    # Test guardrails module
    from aicl.guardrails import (
        validate_message, 
        rate_limit_check, 
        verify_signature,
        sanitize_message
    )
    print("✓ Guardrails module imports successful")
    
    # Test main package imports
    from aicl import (
        new_msg as aicl_new_msg,
        run_server as aicl_run_server,
        AICLLogger as aicl_AICLLogger,
        validate_message as aicl_validate_message
    )
    print("✓ Main package imports successful")
    
    print("\nAll imports successful! AICL is ready to use.")
    
except ImportError as e:
    print(f"✗ Import error: {e}")
except Exception as e:
    print(f"✗ Unexpected error: {e}")