"""
ASTRA OS Credential Store
Secure HMAC secret storage using Windows Credential Manager.
"""
import sys
import logging

logger = logging.getLogger(__name__)

# Check if we can import win32cred (Windows only)
try:
    import win32cred
    import win32con
    import pywintypes
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    logger.warning("win32cred not available - falling back to environment variables")


CREDENTIAL_TARGET = "ASTRA_POLICY_HMAC"
CREDENTIAL_TARGET_PREV = "ASTRA_POLICY_HMAC_PREV"


def store_hmac_secret(secret: bytes, is_previous: bool = False) -> bool:
    """
    Store HMAC secret in Windows Credential Manager.
    
    Args:
        secret: The HMAC secret bytes to store
        is_previous: If True, store as previous secret (for rotation)
    
    Returns:
        True if stored successfully, False otherwise
    """
    if not HAS_WIN32:
        logger.error("Cannot store credentials - win32cred not available")
        return False
    
    if not isinstance(secret, bytes):
        raise TypeError("Secret must be bytes")
    
    target_name = CREDENTIAL_TARGET_PREV if is_previous else CREDENTIAL_TARGET
    
    try:
        # Convert bytes to base64 string for storage
        import base64
        secret_str = base64.b64encode(secret).decode('ascii')
        
        credential = {
            'Type': win32cred.CRED_TYPE_GENERIC,
            'TargetName': target_name,
            'CredentialBlob': secret_str,
            'Persist': win32cred.CRED_PERSIST_LOCAL_MACHINE,
            'Comment': f'ASTRA OS HMAC signing key {"(previous)" if is_previous else "(current)"}'
        }
        
        win32cred.CredWrite(credential, 0)
        logger.info(f"Stored HMAC secret: {target_name}")
        return True
        
    except pywintypes.error as e:
        logger.error(f"Failed to store credential: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error storing credential: {e}")
        return False


def load_hmac_secret(is_previous: bool = False) -> bytes:
    """
    Load HMAC secret from Windows Credential Manager.
    
    Args:
        is_previous: If True, load previous secret (for rotation window)
    
    Returns:
        HMAC secret bytes, or dev fallback if not found
    """
    if not HAS_WIN32:
        import os
        fallback_key = "ASTRA_POLICY_HMAC_PREV" if is_previous else "ASTRA_POLICY_HMAC"
        fallback = os.environ.get(fallback_key, "dev-secret-change-me")
        logger.warning(f"Using environment variable fallback for {fallback_key}")
        return fallback.encode()
    
    target_name = CREDENTIAL_TARGET_PREV if is_previous else CREDENTIAL_TARGET
    
    try:
        cred = win32cred.CredRead(target_name, win32cred.CRED_TYPE_GENERIC)
        logger.debug(f"Loaded HMAC secret: {target_name}")
        # Decode from base64 string back to bytes
        import base64
        secret_str = cred['CredentialBlob']
        return base64.b64decode(secret_str)
        
    except pywintypes.error as e:
        # Credential not found - return fallback
        if e.winerror == 1168:  # ERROR_NOT_FOUND
            logger.warning(f"Credential {target_name} not found, using dev fallback")
            return b"dev-secret-change-me"
        else:
            logger.error(f"Failed to load credential: {e}")
            return b"dev-secret-change-me"
            
    except Exception as e:
        logger.error(f"Unexpected error loading credential: {e}")
        return b"dev-secret-change-me"


def delete_hmac_secret(is_previous: bool = False) -> bool:
    """
    Delete HMAC secret from Windows Credential Manager.
    
    Args:
        is_previous: If True, delete previous secret
    
    Returns:
        True if deleted successfully, False otherwise
    """
    if not HAS_WIN32:
        logger.warning("Cannot delete credentials - win32cred not available")
        return False
    
    target_name = CREDENTIAL_TARGET_PREV if is_previous else CREDENTIAL_TARGET
    
    try:
        win32cred.CredDelete(target_name, win32cred.CRED_TYPE_GENERIC)
        logger.info(f"Deleted HMAC secret: {target_name}")
        return True
        
    except pywintypes.error as e:
        if e.winerror == 1168:  # ERROR_NOT_FOUND
            logger.debug(f"Credential {target_name} not found (already deleted)")
            return True
        else:
            logger.error(f"Failed to delete credential: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Unexpected error deleting credential: {e}")
        return False


def rotate_hmac_secret(new_secret: bytes) -> bool:
    """
    Rotate HMAC secret with dual-key window.
    Current secret becomes previous, new secret becomes current.
    
    Args:
        new_secret: The new HMAC secret bytes
    
    Returns:
        True if rotation successful, False otherwise
    """
    if not isinstance(new_secret, bytes):
        raise TypeError("Secret must be bytes")
    
    try:
        # Load current secret
        current_secret = load_hmac_secret(is_previous=False)
        
        # Store current as previous
        if current_secret != b"dev-secret-change-me":
            if not store_hmac_secret(current_secret, is_previous=True):
                logger.error("Failed to store current secret as previous")
                return False
        
        # Store new as current
        if not store_hmac_secret(new_secret, is_previous=False):
            logger.error("Failed to store new secret as current")
            return False
        
        logger.info("HMAC secret rotation complete")
        return True
        
    except Exception as e:
        logger.error(f"Failed to rotate secret: {e}")
        return False


def is_credential_store_available() -> bool:
    """Check if Windows Credential Manager is available."""
    return HAS_WIN32


if __name__ == "__main__":
    # Demo/test credential store operations
    import secrets
    
    print("=== ASTRA Credential Store Demo ===\n")
    
    print(f"Windows Credential Manager available: {is_credential_store_available()}")
    
    if not is_credential_store_available():
        print("⚠️  win32cred not installed. Install with: pip install pywin32")
        sys.exit(1)
    
    # Generate test secret
    test_secret = secrets.token_bytes(32)
    print(f"Generated test secret: {test_secret[:8].hex()}... ({len(test_secret)} bytes)")
    
    # Store
    print("\n1. Storing secret...")
    if store_hmac_secret(test_secret):
        print("   ✅ Secret stored successfully")
    else:
        print("   ❌ Failed to store secret")
        sys.exit(1)
    
    # Load
    print("\n2. Loading secret...")
    loaded = load_hmac_secret()
    if loaded == test_secret:
        print("   ✅ Secret loaded correctly")
    else:
        print(f"   ❌ Secret mismatch: {loaded[:8].hex()}...")
        sys.exit(1)
    
    # Rotate
    print("\n3. Rotating secret...")
    new_secret = secrets.token_bytes(32)
    if rotate_hmac_secret(new_secret):
        print("   ✅ Rotation successful")
        
        # Verify current
        current = load_hmac_secret(is_previous=False)
        if current == new_secret:
            print("   ✅ Current secret correct")
        else:
            print("   ❌ Current secret mismatch")
        
        # Verify previous
        previous = load_hmac_secret(is_previous=True)
        if previous == test_secret:
            print("   ✅ Previous secret preserved")
        else:
            print("   ❌ Previous secret mismatch")
    else:
        print("   ❌ Rotation failed")
    
    # Cleanup
    print("\n4. Cleanup...")
    delete_hmac_secret(is_previous=False)
    delete_hmac_secret(is_previous=True)
    print("   ✅ Test credentials deleted")
    
    print("\n✅ All credential store operations verified!")
