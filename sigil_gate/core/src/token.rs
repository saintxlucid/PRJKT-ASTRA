use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use uuid::Uuid;
use sha2::{Sha256, Digest};

/// Token budget (enforced at runtime)
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Budget {
    pub cpu_ms: u64,
    pub io_bytes: u64,
    pub net_bytes: u64,
    pub ops: u64,
}

impl Default for Budget {
    fn default() -> Self {
        Self {
            cpu_ms: 5_000,      // 5 seconds
            io_bytes: 1_000_000,  // 1 MB
            net_bytes: 200_000,   // 200 KB
            ops: 50,
        }
    }
}

/// Environment attestation (proves caller identity)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EnvAttestation {
    /// SHA-256 hash of caller binary
    pub caller_hash: [u8; 32],
    
    /// Command line arguments
    pub cmdline: String,
    
    /// Parent process ID
    pub parent_pid: u32,
    
    /// Job object ID (Windows) or cgroup (Linux)
    pub job_object_id: Option<String>,
    
    /// Timestamp (TPM/Roughtime anchor)
    pub signed_at: DateTime<Utc>,
}

/// Token claims (payload)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Claims {
    /// Token version (current: 2)
    pub v: u8,
    
    /// Key ID
    pub kid: String,
    
    /// Issuer (e.g., "ASTRA")
    pub iss: String,
    
    /// Subject (e.g., "proc:1234")
    pub sub: String,
    
    /// Audience ("sigil-gate")
    pub aud: String,
    
    /// Issued at
    pub iat: DateTime<Utc>,
    
    /// Not before
    pub nbf: DateTime<Utc>,
    
    /// Expiry
    pub exp: DateTime<Utc>,
    
    /// Random nonce
    pub nonce: String,
    
    /// Scopes (e.g., ["fs.write:C:/Projects/**"])
    pub scopes: Vec<String>,
    
    /// Budget enforcement
    pub budget: Budget,
    
    /// SHA-256 digest of exact execution plan
    pub plan_digest: [u8; 32],
    
    /// Environment attestation
    pub env_attest: EnvAttestation,
    
    /// Lease ID (for renewable long-lived tokens)
    pub lease_id: Option<Uuid>,
    
    /// Revocation check ID (monotonic)
    pub rev_id: u64,
    
    /// Context metadata
    #[serde(default)]
    pub context: BTreeMap<String, serde_json::Value>,
    
    /// Content type
    pub cty: String,
}

impl Claims {
    /// Compute canonical CBOR bytes for signing
    pub fn canonical_bytes(&self) -> Result<Vec<u8>, serde_cbor::Error> {
        serde_cbor::to_vec(self)
    }
    
    /// Compute plan digest from plan JSON
    pub fn compute_plan_digest(plan_json: &str) -> [u8; 32] {
        let mut hasher = Sha256::new();
        hasher.update(plan_json.as_bytes());
        let result = hasher.finalize();
        let mut digest = [0u8; 32];
        digest.copy_from_slice(&result);
        digest
    }
    
    /// Check if token is expired
    pub fn is_expired(&self, now: DateTime<Utc>) -> bool {
        now > self.exp
    }
    
    /// Check if token is not yet valid
    pub fn is_premature(&self, now: DateTime<Utc>) -> bool {
        now < self.nbf
    }
}

/// Hybrid signature (Dilithium + ECDSA)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HybridSig {
    /// Dilithium signature (base64)
    pub dilithium: String,
    
    /// ECDSA P-256 signature (base64 DER)
    pub ecdsa_p256: String,
}

/// Complete token with claims + hybrid signature
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HybridToken {
    pub claims: Claims,
    pub sig: HybridSig,
}

impl HybridToken {
    /// Get canonical bytes for verification
    pub fn canonical_bytes(&self) -> Result<Vec<u8>, serde_cbor::Error> {
        self.claims.canonical_bytes()
    }
    
    /// Serialize to JSON
    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string_pretty(self)
    }
    
    /// Deserialize from JSON
    pub fn from_json(json: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(json)
    }
    
    /// Check if token matches plan digest
    pub fn verify_plan(&self, plan_json: &str) -> bool {
        let expected = Claims::compute_plan_digest(plan_json);
        self.claims.plan_digest == expected
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_plan_digest_deterministic() {
        let plan1 = r#"{"op": "delete", "path": "X:/test.txt"}"#;
        let plan2 = r#"{"op": "delete", "path": "X:/test.txt"}"#;
        let plan3 = r#"{"op": "delete", "path": "X:/other.txt"}"#;
        
        let digest1 = Claims::compute_plan_digest(plan1);
        let digest2 = Claims::compute_plan_digest(plan2);
        let digest3 = Claims::compute_plan_digest(plan3);
        
        assert_eq!(digest1, digest2);
        assert_ne!(digest1, digest3);
    }

    #[test]
    fn test_token_expiry() {
        let now = Utc::now();
        let claims = Claims {
            v: 2,
            kid: "test".into(),
            iss: "ASTRA".into(),
            sub: "test".into(),
            aud: "sigil-gate".into(),
            iat: now,
            nbf: now,
            exp: now + chrono::Duration::seconds(60),
            nonce: "test".into(),
            scopes: vec![],
            budget: Budget::default(),
            plan_digest: [0u8; 32],
            env_attest: EnvAttestation {
                caller_hash: [0u8; 32],
                cmdline: "test".into(),
                parent_pid: 0,
                job_object_id: None,
                signed_at: now,
            },
            lease_id: None,
            rev_id: 0,
            context: BTreeMap::new(),
            cty: "application/astoken+json".into(),
        };
        
        assert!(!claims.is_expired(now));
        assert!(claims.is_expired(now + chrono::Duration::seconds(61)));
        assert!(!claims.is_premature(now));
    }
}
