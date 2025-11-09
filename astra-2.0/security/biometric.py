"""
ASTRA 2.0 Biometric Security Layer
Advanced voice verification and quantum memory anchoring
"""
import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Optional, Tuple
import librosa
import python_speech_features
from scipy.fft import fft
import logging
from pathlib import Path
import json
import hashlib
from datetime import datetime

from astra.core.sovereign.guardian import get_guardian
from astra.security.activity_audit import audit_event

logger = logging.getLogger("astra.security.biometric")

class VoiceprintModel(nn.Module):
    """Neural voiceprint model for creator verification"""
    
    def __init__(self, input_size: int = 40):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=128,
            num_layers=2,
            batch_first=True,
            bidirectional=True
        )
        self.fc = nn.Linear(256, 512)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass"""
        lstm_out, _ = self.lstm(x)
        # Take last timestep
        last_hidden = lstm_out[:, -1, :]
        embedding = self.fc(last_hidden)
        # L2 normalize
        return nn.functional.normalize(embedding, p=2, dim=1)

class BiometricVerification:
    """Advanced biometric security system"""
    
    def __init__(self):
        self.voiceprint_model = VoiceprintModel()
        self.creator_voiceprints: List[np.ndarray] = []
        self.verification_threshold = 0.85
        self.quantum_seeds: Dict[str, str] = {}
        self._load_creator_voiceprints()
        
    def _load_creator_voiceprints(self) -> None:
        """Load stored creator voiceprints"""
        try:
            voiceprint_path = Path(__file__).parent / "sovereign" / "creator_voiceprints.json"
            if not voiceprint_path.exists():
                logger.warning("No stored voiceprints found")
                return
                
            with open(voiceprint_path) as f:
                data = json.load(f)
                
            # Convert stored vectors back to numpy
            self.creator_voiceprints = [
                np.array(print_data) for print_data in data["voiceprints"]
            ]
            
            logger.info(f"Loaded {len(self.creator_voiceprints)} creator voiceprints")
            
        except Exception as e:
            logger.error(f"Failed to load voiceprints: {str(e)}")
            
    def extract_voice_features(self, audio: np.ndarray, sr: int = 16000) -> np.ndarray:
        """Extract advanced voice features"""
        try:
            # Normalize audio
            audio = audio / np.max(np.abs(audio))
            
            # Extract MFCC features
            mfcc = python_speech_features.mfcc(
                audio,
                sr,
                numcep=40,
                nfilt=40,
                nfft=2048,
                winlen=0.025,
                winstep=0.01
            )
            
            # Extract pitch features
            pitches, magnitudes = librosa.piptrack(
                y=audio,
                sr=sr,
                fmin=70,
                fmax=400
            )
            pitch_mean = np.mean(pitches, axis=1)
            
            # Extract spectral features
            spec = np.abs(librosa.stft(audio))
            spectral_centroid = librosa.feature.spectral_centroid(S=spec)[0]
            spectral_bandwidth = librosa.feature.spectral_bandwidth(S=spec)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(S=spec)[0]
            
            # Combine features
            combined = np.concatenate([
                mfcc,
                pitch_mean.reshape(-1, 1),
                spectral_centroid.reshape(-1, 1),
                spectral_bandwidth.reshape(-1, 1),
                spectral_rolloff.reshape(-1, 1)
            ], axis=1)
            
            return combined
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {str(e)}")
            raise
            
    def verify_voice(self, audio: np.ndarray, sr: int = 16000) -> Tuple[bool, float]:
        """Verify voice against stored creator voiceprints"""
        try:
            # Extract features
            features = self.extract_voice_features(audio, sr)
            
            # Convert to tensor
            features_tensor = torch.FloatTensor(features).unsqueeze(0)
            
            # Get embedding
            with torch.no_grad():
                embedding = self.voiceprint_model(features_tensor)
            embedding = embedding.numpy()
            
            # Compare with stored prints
            similarities = [
                np.dot(embedding, print_vec) 
                for print_vec in self.creator_voiceprints
            ]
            
            max_similarity = max(similarities)
            is_verified = max_similarity > self.verification_threshold
            
            audit_event("security.voice.verified", {
                "verified": is_verified,
                "confidence": float(max_similarity)
            })
            
            return is_verified, max_similarity
            
        except Exception as e:
            logger.error(f"Voice verification failed: {str(e)}")
            return False, 0.0
            
    def generate_quantum_seed(self, audio_features: np.ndarray) -> str:
        """Generate quantum-resistant seed from voice features"""
        try:
            # Extract unique voice characteristics
            spectral_signature = fft(audio_features.flatten())
            phase_angles = np.angle(spectral_signature)
            
            # Combine with timestamp for uniqueness
            timestamp = datetime.now().timestamp()
            combined = np.concatenate([
                phase_angles,
                np.array([timestamp])
            ])
            
            # Generate seed
            seed_bytes = combined.tobytes()
            quantum_seed = hashlib.sha3_512(seed_bytes).hexdigest()
            
            # Store seed
            self.quantum_seeds[quantum_seed] = str(timestamp)
            
            return quantum_seed
            
        except Exception as e:
            logger.error(f"Quantum seed generation failed: {str(e)}")
            raise
            
    def verify_quantum_seed(self, seed: str) -> bool:
        """Verify quantum seed authenticity"""
        return seed in self.quantum_seeds

# Initialize global biometric system
_BIOMETRIC: Optional[BiometricVerification] = None

def init_biometric() -> None:
    """Initialize global biometric system"""
    global _BIOMETRIC
    _BIOMETRIC = BiometricVerification()
    
def get_biometric() -> BiometricVerification:
    """Get global biometric system"""
    global _BIOMETRIC
    if not _BIOMETRIC:
        init_biometric()
    return _BIOMETRIC