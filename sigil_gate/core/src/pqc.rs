use pqcrypto_dilithium::dilithium2::*;
use pqcrypto_traits::sign::{SignedMessage, PublicKey as PQPublicKey, SecretKey as PQSecretKey};
use base64::{engine::general_purpose, Engine as _};
use crate::errors::{Result, SigilError};

/// Dilithium public key wrapper
pub struct DilithiumPub(pub PublicKey);

/// Dilithium secret key wrapper
pub struct DilithiumPriv(pub SecretKey);

/// Generate Dilithium2 keypair
pub fn keypair() -> (DilithiumPub, DilithiumPriv) {
    let (pk, sk) = keypair();
    (DilithiumPub(pk), DilithiumPriv(sk))
}

/// Sign message with Dilithium
pub fn sign(sk: &DilithiumPriv, msg: &[u8]) -> String {
    let signed = sign(msg, &sk.0);
    general_purpose::STANDARD.encode(signed.as_bytes())
}

/// Verify Dilithium signature
pub fn verify(pk: &DilithiumPub, msg: &[u8], sig_b64: &str) -> Result<bool> {
    let sig_bytes = general_purpose::STANDARD
        .decode(sig_b64)
        .map_err(|e| SigilError::CryptoError(format!("Invalid base64: {}", e)))?;

    match open(&sig_bytes, &pk.0) {
        Ok(opened_msg) => Ok(opened_msg == msg),
        Err(_) => Ok(false),
    }
}

/// Serialize public key to base64
pub fn pub_key_to_base64(pk: &DilithiumPub) -> String {
    general_purpose::STANDARD.encode(pk.0.as_bytes())
}

/// Deserialize public key from base64
pub fn pub_key_from_base64(b64: &str) -> Result<DilithiumPub> {
    let bytes = general_purpose::STANDARD
        .decode(b64)
        .map_err(|e| SigilError::CryptoError(format!("Invalid base64: {}", e)))?;
    
    PublicKey::from_bytes(&bytes)
        .map(DilithiumPub)
        .map_err(|_| SigilError::CryptoError("Invalid Dilithium public key".into()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dilithium_sign_verify() {
        let (pk, sk) = keypair();
        let msg = b"test message";
        
        let sig = sign(&sk, msg);
        assert!(verify(&pk, msg, &sig).unwrap());
        assert!(!verify(&pk, b"wrong message", &sig).unwrap());
    }

    #[test]
    fn test_pub_key_serialization() {
        let (pk, _) = keypair();
        let b64 = pub_key_to_base64(&pk);
        let pk2 = pub_key_from_base64(&b64).unwrap();
        
        assert_eq!(pk.0.as_bytes(), pk2.0.as_bytes());
    }
}
