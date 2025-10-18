"""
ASTRA Privacy Protection Protocol (A.P.P.P) Storage Module
Handles encrypted storage and secure file operations
"""

import os
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger("astra.privacy.storage")

def generate_and_store_key(path: Path) -> bytes:
    """Generate and store a new encryption key"""
    key = Fernet.generate_key()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(key)
    # Set restrictive permissions
    os.chmod(path, 0o600)
    return key

def load_key(path: Path) -> bytes:
    """Load the encryption key"""
    if not path.exists():
        raise FileNotFoundError("Encryption key not found. Run setup first.")
    return path.read_bytes()

def _get_cipher(key_path: Optional[Path] = None) -> Fernet:
    """Get Fernet cipher instance"""
    if key_path is None:
        key_path = Path(__file__).parent / ".ast_key"
    key = load_key(key_path)
    return Fernet(key)

def encrypt_bytes(data: bytes, key_path: Optional[Path] = None) -> bytes:
    """Encrypt binary data"""
    cipher = _get_cipher(key_path)
    return cipher.encrypt(data)

def decrypt_bytes(token: bytes, key_path: Optional[Path] = None) -> bytes:
    """Decrypt binary data"""
    cipher = _get_cipher(key_path)
    return cipher.decrypt(token)

def encrypt_str(text: str, key_path: Optional[Path] = None) -> bytes:
    """Encrypt string data"""
    return encrypt_bytes(text.encode(), key_path)

def decrypt_str(token: bytes, key_path: Optional[Path] = None) -> str:
    """Decrypt to string"""
    return decrypt_bytes(token, key_path).decode()

def secure_write(path: Path, data: bytes, encrypt: bool = True):
    """Write data securely to file"""
    path.parent.mkdir(parents=True, exist_ok=True)
    if encrypt:
        data = encrypt_bytes(data)
    path.write_bytes(data)
    os.chmod(path, 0o600)

def secure_write_text(path: Path, text: str, encrypt: bool = True):
    """Write text securely to file"""
    secure_write(path, text.encode(), encrypt)

def secure_read(path: Path, decrypt: bool = True) -> bytes:
    """Read data securely from file"""
    data = path.read_bytes()
    if decrypt:
        data = decrypt_bytes(data)
    return data

def secure_read_text(path: Path, decrypt: bool = True) -> str:
    """Read text securely from file"""
    return secure_read(path, decrypt).decode()

def secure_wipe(path: Path):
    """Securely wipe a file by overwriting with zeros"""
    if not path.exists():
        return
        
    # Get file size
    size = path.stat().st_size
    
    # Overwrite with zeros
    with open(path, "ba+") as f:
        # Seek to beginning
        f.seek(0)
        # Write zeros
        f.write(b"\x00" * size)
        # Ensure writes are flushed to disk
        f.flush()
        os.fsync(f.fileno())
    
    # Finally delete the file
    path.unlink()