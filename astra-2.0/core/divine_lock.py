"""
ASTRA Divine Lock System - Emergency Shutdown Protocol
"""
import os
import time
import json
import asyncio
import logging
import hashlib
import base64
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .biometrics import get_voice_biometrics, VerificationResult

logger = logging.getLogger("astra.divine_lock")

@dataclass
class LockState:
    """Divine Lock state"""
    is_active: bool
    frozen_time: Optional[float]
    lock_reason: Optional[str]
    creator_key: Optional[str]

class DivineLock:
    """ASTRA emergency shutdown system"""
    
    def __init__(self) -> None:
        self.state_file = Path("core/divine_lock.state")
        self.key_file = Path("core/creator.key")
        self.state = LockState(
            is_active=False,
            frozen_time=None,
            lock_reason=None,
            creator_key=None
        )
        self._fernet: Optional[Fernet] = None
        self._biometrics = get_voice_biometrics()
        self._challenge: Optional[str] = None
        self._load_state()
        
    def _generate_key(self, password: str, salt: bytes) -> bytes:
        """Generate encryption key from password"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
        
    def initialize(
        self,
        creator_password: str,
        voice_data: Optional[bytes] = None
    ) -> bool:
        """Initialize Divine Lock with creator password and voice"""
        try:
            # Generate salt
            salt = os.urandom(16)
            
            # Generate key
            key = self._generate_key(creator_password, salt)
            
            # Create Fernet cipher
            self._fernet = Fernet(key)
            
            # Encrypt test message
            test_message = "ASTRA_DIVINE_LOCK"
            encrypted = self._fernet.encrypt(test_message.encode())
            
            # Verify encryption
            decrypted = self._fernet.decrypt(encrypted).decode()
            if decrypted != test_message:
                raise ValueError("Encryption verification failed")
                
            # Save salt and encrypted test
            self.key_file.write_bytes(
                salt + encrypted
            )
            
            # Update state
            self.state.creator_key = key.decode()
            self._save_state()
            
            # Enroll voice if provided
            if voice_data:
                audio = np.frombuffer(voice_data, dtype=np.float32)
                if not self._biometrics.enroll_voice(audio):
                    logger.warning("Voice enrollment failed")
            
            logger.info("Divine Lock initialized")
            return True
            
        except Exception as e:
            logger.error(f"Divine Lock initialization failed: {str(e)}")
            return False
            
    def verify_creator(
        self,
        password: str,
        voice_data: Optional[bytes] = None
    ) -> Tuple[bool, Optional[str]]:
        """Verify creator password and voice"""
        try:
            if not self.key_file.exists():
                return False, "No Divine Lock initialized", "No Divine Lock initialized"
                
            # Read salt and test message
            data = self.key_file.read_bytes()
            salt = data[:16]
            encrypted = data[16:]
            
            # Generate key
            key = self._generate_key(password, salt)
            test_fernet = Fernet(key)
            
            # Try to decrypt
            try:
                decrypted = test_fernet.decrypt(encrypted).decode()
                if decrypted != "ASTRA_DIVINE_LOCK":
                    return False, "Invalid password"
            except:
                return False, "Invalid password"
                
            # Verify voice if provided
            if voice_data:
                audio = np.frombuffer(voice_data, dtype=np.float32)
                result = self._biometrics.verify_voice(
                    audio,
                    self._challenge
                )
                if not result.passed:
                    return False, result.error
                    
                # Clear challenge
                self._challenge = None
                
            return True, None
                
        except Exception as e:
            logger.error(f"Creator verification failed: {str(e)}")
            return False
            
    async def activate_lock(self, reason: str) -> bool:
        """Activate Divine Lock"""
        try:
            if self.state.is_active:
                return True
                
            self.state.is_active = True
            self.state.frozen_time = time.time()
            self.state.lock_reason = reason
            
            self._save_state()
            
            logger.warning(f"Divine Lock activated: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Divine Lock activation failed: {str(e)}")
            return False
            
    async def deactivate_lock(
        self,
        creator_password: str,
        voice_data: Optional[bytes] = None
    ) -> bool:
        """Deactivate Divine Lock with creator verification"""
        try:
            if not self.state.is_active:
                return True
                
            verified, error = self.verify_creator(
                creator_password,
                voice_data
            )
            if not verified:
                logger.error(f"Creator verification failed: {error}")
                return False
                
            self.state.is_active = False
            self.state.frozen_time = None
            self.state.lock_reason = None
            
            self._save_state()
            
            logger.info("Divine Lock deactivated by creator")
            return True
            
        except Exception as e:
            logger.error(f"Divine Lock deactivation failed: {str(e)}")
            return False
            
    def get_state(self) -> LockState:
        """Get current Divine Lock state"""
        return self.state
        
    def get_challenge(self) -> str:
        """Get voice verification challenge"""
        self._challenge = self._biometrics.generate_challenge()
        return self._challenge
        
    def enroll_voice(self, voice_data: bytes) -> bool:
        """Enroll additional voice sample"""
        try:
            audio = np.frombuffer(voice_data, dtype=np.float32)
            return self._biometrics.enroll_voice(audio)
        except Exception as e:
            logger.error(f"Voice enrollment failed: {str(e)}")
            return False
        
    def _load_state(self) -> None:
        """Load Divine Lock state from file"""
        try:
            if self.state_file.exists():
                data = json.loads(self.state_file.read_text())
                self.state = LockState(**data)
        except Exception as e:
            logger.error(f"Failed to load Divine Lock state: {str(e)}")
            
    def _save_state(self) -> None:
        """Save Divine Lock state to file"""
        try:
            self.state_file.write_text(
                json.dumps({
                    "is_active": self.state.is_active,
                    "frozen_time": self.state.frozen_time,
                    "lock_reason": self.state.lock_reason,
                    "creator_key": self.state.creator_key
                })
            )
        except Exception as e:
            logger.error(f"Failed to save Divine Lock state: {str(e)}")

_instance = None

def get_divine_lock() -> DivineLock:
    """Get Divine Lock singleton"""
    global _instance
    if _instance is None:
        _instance = DivineLock()
    return _instance