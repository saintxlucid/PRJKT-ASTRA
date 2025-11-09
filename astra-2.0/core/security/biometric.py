"""
ASTRA Biometric Security System
"""
import numpy as np
import librosa
import torch
from typing import Tuple
from ..core.logging import get_logger
from ..core.security.quantum import get_quantum

logger = get_logger(__name__)

class BiometricVerification:
    def __init__(self):
        self.model = self._load_model()
        self._quantum = get_quantum()
        
    def _load_model(self) -> torch.nn.Module:
        """Load the voice verification model"""
        try:
            model = torch.load("models/voiceprint_v2.pt")
            model.eval()
            return model
        except Exception as e:
            logger.error(f"Failed to load voiceprint model: {e}")
            raise
            
    def extract_voice_features(self, audio: np.ndarray) -> np.ndarray:
        """Extract MFCC and other voice features"""
        # Extract MFCCs
        mfccs = librosa.feature.mfcc(y=audio, sr=16000, n_mfcc=40)
        
        # Get pitch features
        pitches, magnitudes = librosa.piptrack(y=audio, sr=16000)
        
        # Combine features
        features = np.concatenate([
            mfccs.flatten(),
            pitches.mean(axis=1),
            magnitudes.std(axis=1)
        ])
        
        return features
        
    def verify_voice(self, audio: np.ndarray) -> Tuple[bool, float]:
        """
        Verify voice against stored template
        Returns: (is_verified, confidence)
        """
        try:
            # Extract features
            features = self.extract_voice_features(audio)
            features_tensor = torch.from_numpy(features).float()
            
            # Get stored template
            template = self._load_template()
            
            # Compare with model
            with torch.no_grad():
                confidence = self.model(features_tensor, template)
                
            is_verified = confidence > 0.85
            return is_verified, float(confidence)
            
        except Exception as e:
            logger.error(f"Voice verification failed: {e}")
            return False, 0.0
            
    def generate_quantum_seed(self, features: np.ndarray) -> str:
        """Generate quantum seed from voice features"""
        # Use high entropy features only
        entropy_mask = self._get_entropy_mask(features)
        quantum_features = features[entropy_mask]
        
        # Generate seed
        seed = self._quantum.generate_seed(quantum_features)
        return seed
        
    def _get_entropy_mask(self, features: np.ndarray) -> np.ndarray:
        """Get mask of high entropy feature indices"""
        # Calculate entropy per feature
        eps = 1e-10
        probs = np.abs(features) / (np.sum(np.abs(features)) + eps)
        entropy = -np.sum(probs * np.log2(probs + eps))
        
        # Keep top 20% highest entropy features
        k = int(0.2 * len(features))
        indices = np.argpartition(entropy, -k)[-k:]
        
        mask = np.zeros_like(features, dtype=bool)
        mask[indices] = True
        return mask
        
    def _load_template(self) -> torch.Tensor:
        """Load stored voice template"""
        try:
            template = torch.load("models/creator_template.pt")
            return template
        except Exception as e:
            logger.error(f"Failed to load voice template: {e}")
            raise

_instance = None

def get_biometric() -> BiometricVerification:
    """Get biometric verification singleton"""
    global _instance
    if _instance is None:
        _instance = BiometricVerification()
    return _instance