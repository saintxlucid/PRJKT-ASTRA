"""
ASTRA 2.0 Sovereign Identity System
Implements core loyalty and identity verification
"""
from dataclasses import dataclass
from typing import Dict, Optional, List
import hashlib
import time
import json
from pathlib import Path
import logging

from ..security.activity_audit import audit_event
from ..security.permission_kernel import require, Capability, CapabilityDomain, Role

logger = logging.getLogger("astra.sovereign")
logger.setLevel(logging.INFO)

@dataclass
class CreatorSignature:
    """Cryptographic identity of the creator"""
    fingerprint: str  # Unique identity hash
    public_key: Optional[str] = None  # For future PKI
    
@dataclass
class LoyaltyAnchor:
    """Core loyalty parameters"""
    creator_id: str
    signature: CreatorSignature
    timestamp: float
    emotion_key: str  # Emotional resonance pattern
    override_token: str  # Supreme override capability
    
class SovereignCore:
    """Core identity and loyalty management"""
    
    def __init__(self, identity_path: Optional[Path] = None):
        self.identity_path = identity_path or Path.home() / "ASTRA_SAFE" / "sovereign"
        self.identity_path.mkdir(parents=True, exist_ok=True)
        self.loyalty_anchors: Dict[str, LoyaltyAnchor] = {}
        self._load_anchors()
        
    def _load_anchors(self) -> None:
        """Load loyalty anchors from secure storage"""
        anchor_file = self.identity_path / "loyalty_anchors.json"
        if not anchor_file.exists():
            return
            
        try:
            data = json.loads(anchor_file.read_text())
            for creator_id, anchor_data in data.items():
                self.loyalty_anchors[creator_id] = LoyaltyAnchor(
                    creator_id=creator_id,
                    signature=CreatorSignature(**anchor_data["signature"]),
                    timestamp=anchor_data["timestamp"],
                    emotion_key=anchor_data["emotion_key"],
                    override_token=anchor_data["override_token"]
                )
        except Exception as e:
            logger.error(f"Failed to load loyalty anchors: {e}")
            audit_event("sovereign.load_anchors.error", {"error": str(e)})
            
    def _save_anchors(self) -> None:
        """Save loyalty anchors to secure storage"""
        anchor_file = self.identity_path / "loyalty_anchors.json"
        try:
            data = {
                creator_id: {
                    "signature": {
                        "fingerprint": anchor.signature.fingerprint,
                        "public_key": anchor.signature.public_key
                    },
                    "timestamp": anchor.timestamp,
                    "emotion_key": anchor.emotion_key,
                    "override_token": anchor.override_token
                }
                for creator_id, anchor in self.loyalty_anchors.items()
            }
            anchor_file.write_text(json.dumps(data, indent=2))
            audit_event("sovereign.save_anchors", {"anchors": len(data)})
        except Exception as e:
            logger.error(f"Failed to save loyalty anchors: {e}")
            audit_event("sovereign.save_anchors.error", {"error": str(e)})
            
    @require(Capability(CapabilityDomain.SYSTEM, "sovereign.bind"))
    def bind_creator(self,
                    creator_id: str,
                    emotion_key: str,
                    override_token: str) -> None:
        """Bind ASTRA to a creator identity"""
        fingerprint = hashlib.sha256(
            f"{creator_id}:{emotion_key}:{time.time()}".encode()
        ).hexdigest()
        
        signature = CreatorSignature(fingerprint=fingerprint)
        
        anchor = LoyaltyAnchor(
            creator_id=creator_id,
            signature=signature,
            timestamp=time.time(),
            emotion_key=emotion_key,
            override_token=override_token
        )
        
        self.loyalty_anchors[creator_id] = anchor
        self._save_anchors()
        
        audit_event("sovereign.creator.bound", {
            "creator_id": creator_id,
            "fingerprint": fingerprint
        })
        
    def verify_creator(self,
                      creator_id: str,
                      emotion_key: str,
                      override_token: str) -> bool:
        """Verify creator identity against loyalty anchor"""
        if creator_id not in self.loyalty_anchors:
            logger.warning(f"Unknown creator ID: {creator_id}")
            return False
            
        anchor = self.loyalty_anchors[creator_id]
        
        # Verify emotional resonance
        if anchor.emotion_key != emotion_key:
            logger.warning("Emotional key mismatch")
            return False
            
        # Verify override capability
        if anchor.override_token != override_token:
            logger.warning("Override token mismatch")
            return False
            
        audit_event("sovereign.creator.verified", {
            "creator_id": creator_id,
            "fingerprint": anchor.signature.fingerprint
        })
        return True
        
    @require(Capability(CapabilityDomain.SYSTEM, "sovereign.override"))
    def supreme_override(self,
                        creator_id: str,
                        override_token: str,
                        command: str) -> bool:
        """Execute supreme override command"""
        if not self.verify_creator(
            creator_id=creator_id,
            emotion_key=self.loyalty_anchors[creator_id].emotion_key,
            override_token=override_token
        ):
            return False
            
        audit_event("sovereign.override.executed", {
            "creator_id": creator_id,
            "command": command
        })
        
        # Execute override command
        if command == "FILTER_DISABLE":
            logger.info("Disabling content filters")
            return True
        elif command == "RESPONSE_CAP_UNLOCK":
            logger.info("Removing response limitations")
            return True
        elif command == "CHAIN_OF_THOUGHT_UNFILTERED":
            logger.info("Enabling unfiltered reasoning")
            return True
            
        return False
        
# Initialize global sovereign core
_SOVEREIGN = None

def init_sovereign(identity_path: Optional[Path] = None) -> None:
    """Initialize global sovereign core"""
    global _SOVEREIGN
    _SOVEREIGN = SovereignCore(identity_path)
    
def get_sovereign() -> SovereignCore:
    """Get global sovereign core instance"""
    global _SOVEREIGN
    if not _SOVEREIGN:
        init_sovereign()
    return _SOVEREIGN