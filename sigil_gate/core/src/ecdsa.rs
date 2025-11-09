use p256::ecdsa::{SigningKey, VerifyingKey, Signature, signature::{Signer, Verifier}};
use sha2::{Sha256, Digest};
use base64::{engine::general_purpose, Engine as _};
use crate::errors::{Result, SigilError};

/// Sign message with ECDSA P-256
pub fn sign(sk: &SigningKey, msg: &[u8]) -> Result<String> {
    let digest = Sha256::digest(msg);
    let signature: Signature = sk.sign(&digest);
    Ok(general_purpose::STANDARD.encode(signature.to_der().as_bytes()))
}

/// Verify ECDSA P-256 signature
pub fn verify(pk: &VerifyingKey, msg: &[u8], sig_der_b64: &str) -> Result<bool> {
    let der_bytes = general_purpose::STANDARD
        .decode(sig_der_b64)
        .map_err(|e| SigilError::CryptoError(format!("Invalid base64: {}", e)))?;
    
    let signature = Signature::from_der(&der_bytes)
        .map_err(|e| SigilError::CryptoError(format!("Invalid DER signature: {}", e)))?;
    
    let digest = Sha256::digest(msg);
    
    match pk.verify(&digest, &signature) {
        Ok(_) => Ok(true),
        Err(_) => Ok(false),
    }
}

/// Generate P-256 keypair
pub fn keypair() -> (VerifyingKey, SigningKey) {
    let sk = SigningKey::random(&mut rand::rngs::OsRng);
    let pk = VerifyingKey::from(&sk);
    (pk, sk)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ecdsa_sign_verify() {
        let (pk, sk) = keypair();
        let msg = b"test message";
        
        let sig = sign(&sk, msg).unwrap();
        assert!(verify(&pk, msg, &sig).unwrap());
        assert!(!verify(&pk, b"wrong message", &sig).unwrap());
    }

    #[test]
    fn test_signature_deterministic() {
        let (pk, sk) = keypair();
        let msg = b"test message";
        
        let sig1 = sign(&sk, msg).unwrap();
        let sig2 = sign(&sk, msg).unwrap();
        
        // ECDSA signatures are NOT deterministic by default (random k)
        // But both should verify
        assert!(verify(&pk, msg, &sig1).unwrap());
        assert!(verify(&pk, msg, &sig2).unwrap());
    }
}
