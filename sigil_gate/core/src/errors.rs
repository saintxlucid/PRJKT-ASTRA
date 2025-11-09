use thiserror::Error;

#[derive(Debug, Error)]
pub enum SigilError {
    #[error("Token verification failed: {0}")]
    VerificationFailed(String),
    
    #[error("Token expired at {0}")]
    TokenExpired(String),
    
    #[error("Token not yet valid (nbf: {0})")]
    TokenNotYetValid(String),
    
    #[error("Token revoked: {0}")]
    TokenRevoked(String),
    
    #[error("Scope denied: {0}")]
    ScopeDenied(String),
    
    #[error("Plan digest mismatch: expected {expected}, got {actual}")]
    PlanMismatch { expected: String, actual: String },
    
    #[error("Environment attestation failed: {0}")]
    EnvAttestationFailed(String),
    
    #[error("Lease expired at {0}")]
    LeaseExpired(String),
    
    #[error("Lease not found: {0}")]
    LeaseNotFound(String),
    
    #[error("Revocation ID mismatch")]
    RevocationIdMismatch,
    
    #[error("Multi-sig threshold not met: {current}/{required}")]
    MultiSigThresholdNotMet { current: usize, required: usize },
    
    #[error("Database error: {0}")]
    DatabaseError(String),
    
    #[error("Serialization error: {0}")]
    SerializationError(String),
    
    #[error("Crypto error: {0}")]
    CryptoError(String),
    
    #[error("Invalid token format")]
    InvalidTokenFormat,
}

impl From<rusqlite::Error> for SigilError {
    fn from(err: rusqlite::Error) -> Self {
        SigilError::DatabaseError(err.to_string())
    }
}

impl From<serde_json::Error> for SigilError {
    fn from(err: serde_json::Error) -> Self {
        SigilError::SerializationError(err.to_string())
    }
}

impl From<serde_cbor::Error> for SigilError {
    fn from(err: serde_cbor::Error) -> Self {
        SigilError::SerializationError(err.to_string())
    }
}

pub type Result<T> = std::result::Result<T, SigilError>;
