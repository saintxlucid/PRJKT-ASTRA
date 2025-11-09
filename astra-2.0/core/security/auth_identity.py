"""
ASTRA 2.0 Authentication Identity - User Identity and Access Management
"""
import hmac
import json
import secrets
from typing import Dict, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass, asdict
from .activity_audit import audit_action

@dataclass
class Identity:
    user_id: str
    roles: Set[str]
    api_key: str
    name: Optional[str] = None
    email: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data["roles"] = list(data["roles"])  # Convert set to list
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Identity":
        """Create Identity from dictionary"""
        data["roles"] = set(data["roles"])  # Convert list to set
        return cls(**data)

class IdentityManager:
    def __init__(self, store_path: Optional[str] = None) -> None:
        """Initialize identity manager with optional custom store path"""
        if not store_path:
            store_path = str(Path.home() / ".astra2" / "identities.json")
            
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_identities()
        
    def _load_identities(self) -> None:
        """Load identities from JSON store"""
        self.identities: Dict[str, Identity] = {}
        
        if self.store_path.exists():
            with open(self.store_path) as f:
                data = json.load(f)
                for identity_data in data:
                    identity = Identity.from_dict(identity_data)
                    self.identities[identity.user_id] = identity
                    
    def _save_identities(self) -> None:
        """Save identities to JSON store"""
        data = [identity.to_dict() for identity in self.identities.values()]
        with open(self.store_path, "w") as f:
            json.dump(data, f, indent=2)
            
    def create_identity(self, 
                       user_id: str,
                       roles: Set[str],
                       name: Optional[str] = None,
                       email: Optional[str] = None) -> Identity:
        """Create new identity with API key"""
        if user_id in self.identities:
            raise ValueError(f"Identity already exists: {user_id}")
            
        api_key = secrets.token_urlsafe(32)
        
        identity = Identity(
            user_id=user_id,
            roles=roles,
            api_key=api_key,
            name=name,
            email=email
        )
        
        self.identities[user_id] = identity
        self._save_identities()
        
        audit_action("identity.created", {
            "user_id": user_id,
            "roles": list(roles)
        })
        
        return identity
    
    def validate_api_key(self, api_key: str) -> Optional[Identity]:
        """Validate API key and return associated identity"""
        for identity in self.identities.values():
            if hmac.compare_digest(identity.api_key, api_key):
                return identity
        return None
    
    def get_identity(self, user_id: str) -> Optional[Identity]:
        """Get identity by user ID"""
        return self.identities.get(user_id)
    
    def update_roles(self, user_id: str, roles: Set[str]) -> Optional[Identity]:
        """Update roles for existing identity"""
        identity = self.identities.get(user_id)
        if not identity:
            return None
            
        identity.roles = roles
        self._save_identities()
        
        audit_action("identity.roles_updated", {
            "user_id": user_id,
            "roles": list(roles)
        })
        
        return identity
    
    def rotate_api_key(self, user_id: str) -> Optional[str]:
        """Generate new API key for identity"""
        identity = self.identities.get(user_id)
        if not identity:
            return None
            
        new_key = secrets.token_urlsafe(32)
        identity.api_key = new_key
        self._save_identities()
        
        audit_action("identity.key_rotated", {
            "user_id": user_id
        })
        
        return new_key

# Global identity manager instance        
manager = IdentityManager()