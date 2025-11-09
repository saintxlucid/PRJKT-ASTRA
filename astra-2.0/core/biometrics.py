"""
ASTRA Voice Biometrics System
"""
import os
import hashlib
import hmac
import time
import json
import base64
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

import librosa
import torch
from scipy import signal
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger("astra.biometrics")

@dataclass
class BiometricTemplate:
    """Voice biometric template"""
    template_hash: str
    salt: str
    embedding_shape: Tuple[int, ...]
    enrollment_count: int
    last_updated: float
    environments: List[str]

@dataclass
class VerificationResult:
    """Voice verification result"""
    passed: bool
    score: float
    liveness_score: float
    challenge_passed: bool
    error: Optional[str] = None

class VoiceBiometrics:
    """ASTRA voice biometrics system"""
    
    def __init__(self) -> None:
        # Configuration
        self.sample_rate = 44100
        self.n_mfcc = 40
        self.min_enrollments = 3
        self.verification_threshold = 0.85
        self.liveness_threshold = 0.75
        self.max_verification_attempts = 3
        self.verification_cooldown = 30  # seconds
        
        # Storage paths
        self.template_dir = Path("core/biometric/templates")
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # Load keys from secure storage
        self.hmac_key = self._load_hmac_key()
        
        # State
        self.last_verification = 0.0
        self.failed_attempts = 0
        self.current_challenge = None
        
    def _load_hmac_key(self) -> bytes:
        """Load HMAC key from secure storage"""
        # TODO: Integrate with KMS
        key_file = Path("core/biometric/hmac.key")
        if not key_file.exists():
            key = os.urandom(32)
            key_file.write_bytes(key)
            return key
        return key_file.read_bytes()
        
    def _extract_features(self, audio: np.ndarray) -> np.ndarray:
        """Extract MFCC features from audio"""
        # Trim silence
        audio, _ = librosa.effects.trim(audio, top_db=20)
        
        # Extract MFCCs and deltas
        mfcc = librosa.feature.mfcc(
            y=audio,
            sr=self.sample_rate,
            n_mfcc=self.n_mfcc
        )
        delta = librosa.feature.delta(mfcc)
        delta2 = librosa.feature.delta(mfcc, order=2)
        
        # Stack features
        features = np.vstack([mfcc, delta, delta2])
        
        # Pool to fixed length
        pooled = np.concatenate([
            features.mean(axis=1),
            features.std(axis=1),
            features.max(axis=1),
            features.min(axis=1)
        ])
        
        # Normalize
        scaler = StandardScaler()
        normalized = scaler.fit_transform(
            pooled.reshape(-1, 1)
        ).ravel()
        
        return normalized
        
    def _check_liveness(
        self,
        audio: np.ndarray,
        challenge: Optional[str] = None
    ) -> Tuple[bool, float]:
        """Check for voice liveness and playback detection"""
        try:
            # Check audio quality
            if len(audio) < self.sample_rate:
                return False, 0.0
                
            # Check for suspicious frequency patterns
            freqs, times, spec = signal.spectrogram(
                audio,
                fs=self.sample_rate
            )
            
            # Look for speaker artifacts
            artifact_score = np.mean(
                spec[freqs > 16000]
            )
            if artifact_score > 0.1:
                return False, 0.0
                
            # Check for natural variations
            energy_std = np.std(
                librosa.feature.rms(y=audio)[0]
            )
            if energy_std < 0.01:
                return False, 0.0
                
            # Validate challenge response if provided
            if challenge and self.current_challenge:
                if challenge != self.current_challenge:
                    return False, 0.0
                    
            # Calculate overall liveness score
            liveness_score = 1.0 - artifact_score
            liveness_score *= min(energy_std * 10, 1.0)
            
            return liveness_score >= self.liveness_threshold, liveness_score
            
        except Exception as e:
            logger.error(f"Liveness check failed: {str(e)}")
            return False, 0.0
            
    def _create_template(
        self,
        embedding: np.ndarray,
        salt: Optional[str] = None
    ) -> BiometricTemplate:
        """Create cancelable biometric template"""
        if not salt:
            salt = base64.b64encode(os.urandom(16)).decode()
            
        # Create template hash
        template_bytes = embedding.tobytes() + salt.encode()
        template_hash = hmac.new(
            key=self.hmac_key,
            msg=template_bytes,
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return BiometricTemplate(
            template_hash=template_hash,
            salt=salt,
            embedding_shape=embedding.shape,
            enrollment_count=1,
            last_updated=time.time(),
            environments=["default"]
        )
        
    def enroll_voice(
        self,
        audio: np.ndarray,
        environment: str = "default"
    ) -> bool:
        """Enroll voice sample"""
        try:
            # Extract features
            features = self._extract_features(audio)
            
            # Check if existing template
            template_file = self.template_dir / "voice_template.json"
            if template_file.exists():
                # Load existing template
                data = json.loads(template_file.read_text())
                template = BiometricTemplate(**data)
                
                # Update template
                template.enrollment_count += 1
                template.last_updated = time.time()
                if environment not in template.environments:
                    template.environments.append(environment)
                    
                if template.enrollment_count >= self.min_enrollments:
                    logger.info("Voice enrollment complete")
                    
            else:
                # Create new template
                template = self._create_template(features)
                
            # Save template
            template_file.write_text(json.dumps({
                "template_hash": template.template_hash,
                "salt": template.salt,
                "embedding_shape": template.embedding_shape,
                "enrollment_count": template.enrollment_count,
                "last_updated": template.last_updated,
                "environments": template.environments
            }))
            
            return True
            
        except Exception as e:
            logger.error(f"Voice enrollment failed: {str(e)}")
            return False
            
    def verify_voice(
        self,
        audio: np.ndarray,
        challenge: Optional[str] = None
    ) -> VerificationResult:
        """Verify voice against stored template"""
        try:
            # Check rate limiting
            now = time.time()
            if now - self.last_verification < self.verification_cooldown:
                return VerificationResult(
                    passed=False,
                    score=0.0,
                    liveness_score=0.0,
                    challenge_passed=False,
                    error="Rate limited"
                )
                
            if self.failed_attempts >= self.max_verification_attempts:
                return VerificationResult(
                    passed=False,
                    score=0.0,
                    liveness_score=0.0,
                    challenge_passed=False,
                    error="Max attempts exceeded"
                )
                
            # Check liveness
            is_live, liveness_score = self._check_liveness(
                audio,
                challenge
            )
            if not is_live:
                self.failed_attempts += 1
                return VerificationResult(
                    passed=False,
                    score=0.0,
                    liveness_score=liveness_score,
                    challenge_passed=challenge == self.current_challenge,
                    error="Liveness check failed"
                )
                
            # Extract features
            features = self._extract_features(audio)
            
            # Load template
            template_file = self.template_dir / "voice_template.json"
            if not template_file.exists():
                return VerificationResult(
                    passed=False,
                    score=0.0,
                    liveness_score=liveness_score,
                    challenge_passed=challenge == self.current_challenge,
                    error="No template found"
                )
                
            template = BiometricTemplate(
                **json.loads(template_file.read_text())
            )
            
            # Verify template hash
            verify_bytes = features.tobytes() + template.salt.encode()
            verify_hash = hmac.new(
                key=self.hmac_key,
                msg=verify_bytes,
                digestmod=hashlib.sha256
            ).hexdigest()
            
            # Compare hashes with constant-time comparison
            score = 1.0 if hmac.compare_digest(
                verify_hash,
                template.template_hash
            ) else 0.0
            
            # Update state
            self.last_verification = now
            if score >= self.verification_threshold:
                self.failed_attempts = 0
                return VerificationResult(
                    passed=True,
                    score=score,
                    liveness_score=liveness_score,
                    challenge_passed=challenge == self.current_challenge
                )
            else:
                self.failed_attempts += 1
                return VerificationResult(
                    passed=False,
                    score=score,
                    liveness_score=liveness_score,
                    challenge_passed=challenge == self.current_challenge,
                    error="Verification failed"
                )
                
        except Exception as e:
            logger.error(f"Voice verification failed: {str(e)}")
            return VerificationResult(
                passed=False,
                score=0.0,
                liveness_score=0.0,
                challenge_passed=False,
                error=str(e)
            )
            
    def generate_challenge(self) -> str:
        """Generate voice challenge phrase"""
        phrases = [
            "ASTRA divine shield activate",
            "Enable sovereign protection now",
            "Initiate creator verification sequence",
            "Begin quantum memory anchor protocol",
            "Execute divine sleep command alpha"
        ]
        self.current_challenge = np.random.choice(phrases)
        return self.current_challenge
        
    def revoke_template(self) -> bool:
        """Revoke and delete biometric template"""
        try:
            template_file = self.template_dir / "voice_template.json"
            if template_file.exists():
                template_file.unlink()
            return True
        except Exception as e:
            logger.error(f"Template revocation failed: {str(e)}")
            return False

_instance = None

def get_voice_biometrics() -> VoiceBiometrics:
    """Get voice biometrics singleton"""
    global _instance
    if _instance is None:
        _instance = VoiceBiometrics()
    return _instance