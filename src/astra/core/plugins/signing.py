"""
Cryptographic signing for plugin audit logs.
Provides integrity verification of plugin action records.
"""
from __future__ import annotations

import base64
import json
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
import structlog

logger = structlog.get_logger()

class AuditSigner:
    """Handles cryptographic signing of audit records"""
    
    def __init__(
        self,
        key_dir: Optional[Path] = None,
        key_size: int = 2048
    ):
        self.key_dir = key_dir or Path("data/keys")
        self.key_size = key_size
        self.key_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or generate keys
        self.private_key, self.public_key = self._load_or_generate_keys()
        
    def _load_or_generate_keys(self) -> Tuple[RSAPrivateKey, RSAPublicKey]:
        """Load existing keys or generate new ones"""
        private_path = self.key_dir / "audit_private.pem"
        public_path = self.key_dir / "audit_public.pem"
        
        if private_path.exists() and public_path.exists():
            # Load existing keys
            with private_path.open("rb") as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None
                )
            
            with public_path.open("rb") as f:
                public_key = serialization.load_pem_public_key(f.read())
                
            return private_key, public_key
            
        else:
            # Generate new key pair
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=self.key_size
            )
            public_key = private_key.public_key()
            
            # Save private key
            pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            with private_path.open("wb") as f:
                f.write(pem)
                
            # Save public key
            pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            with public_path.open("wb") as f:
                f.write(pem)
                
            return private_key, public_key
            
    def sign_record(self, record: Dict) -> str:
        """
        Sign an audit record
        
        Args:
            record: Audit record to sign
            
        Returns:
            str: Base64-encoded signature
        """
        # Canonicalize record to ensure consistent serialization
        canonical = json.dumps(record, sort_keys=True)
        
        # Sign the canonical form
        signature = self.private_key.sign(
            canonical.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode()
        
    def verify_record(self, record: Dict, signature: str) -> bool:
        """
        Verify signature of an audit record
        
        Args:
            record: Audit record to verify
            signature: Base64-encoded signature
            
        Returns:
            bool: True if signature is valid
        """
        try:
            # Decode signature
            sig_bytes = base64.b64decode(signature)
            
            # Canonicalize record
            canonical = json.dumps(record, sort_keys=True)
            
            # Verify signature
            self.public_key.verify(
                sig_bytes,
                canonical.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
            
        except Exception as e:
            logger.error("Signature verification failed", error=str(e))
            return False