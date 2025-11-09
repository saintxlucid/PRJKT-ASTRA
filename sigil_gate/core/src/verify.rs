use chrono::Utc;
use p256::ecdsa::{SigningKey, VerifyingKey};
use crate::{pqc, ecdsa, token::HybridToken, errors::{Result, SigilError}, revocation::RevocationList};

/// Key references for verification
pub struct KeyRefs<'a> {
    pub dilithium_pk: &'a pqc::DilithiumPub,
    pub ecdsa_pk: &'a VerifyingKey,
}

/// Hybrid verify (Dilithium AND ECDSA must both pass)
pub fn hybrid_verify(token: &HybridToken, keys: KeyRefs) -> Result<bool> {
    let msg = token.canonical_bytes()?;
    
    let ok_pqc = pqc::verify(keys.dilithium_pk, &msg, &token.sig.dilithium)?;
    let ok_ecdsa = ecdsa::verify(keys.ecdsa_pk, &msg, &token.sig.ecdsa_p256)?;
    
    Ok(ok_pqc && ok_ecdsa)
}

/// Sign token with hybrid keys
pub fn hybrid_sign(
    token: &mut HybridToken,
    dilithium_sk: &pqc::DilithiumPriv,
    ecdsa_sk: &SigningKey,
) -> Result<()> {
    let msg = token.canonical_bytes()?;
    
    let sig_dilithium = pqc::sign(dilithium_sk, &msg);
    let sig_ecdsa = ecdsa::sign(ecdsa_sk, &msg)?;
    
    token.sig.dilithium = sig_dilithium;
    token.sig.ecdsa_p256 = sig_ecdsa;
    
    Ok(())
}

/// Complete token verification (signature + expiry + revocation)
pub fn verify_token(
    token: &HybridToken,
    keys: KeyRefs,
    crl: Option<&RevocationList>,
) -> Result<()> {
    let now = Utc::now();
    
    // Check expiry
    if token.claims.is_expired(now) {
        return Err(SigilError::TokenExpired(token.claims.exp.to_rfc3339()));
    }
    
    // Check not-before
    if token.claims.is_premature(now) {
        return Err(SigilError::TokenNotYetValid(token.claims.nbf.to_rfc3339()));
    }
    
    // Check revocation
    if let Some(crl) = crl {
        if crl.is_revoked(&token.claims.kid)? {
            if let Some(rev) = crl.get_revocation(&token.claims.kid)? {
                return Err(SigilError::TokenRevoked(format!(
                    "Revoked at {} by {}: {}",
                    rev.revoked_at, rev.issuer, rev.reason
                )));
            }
        }
        
        // Check rev_id matches latest
        let latest_rev_id = crl.latest_rev_id()?;
        if token.claims.rev_id < latest_rev_id {
            return Err(SigilError::RevocationIdMismatch);
        }
    }
    
    // Verify signatures
    if !hybrid_verify(token, keys)? {
        return Err(SigilError::VerificationFailed("Signature verification failed".into()));
    }
    
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::token::{Claims, Budget, EnvAttestation, HybridToken, HybridSig};
    use chrono::Utc;
    use std::collections::BTreeMap;

    #[test]
    fn test_hybrid_sign_verify() {
        let (dilithium_pk, dilithium_sk) = pqc::keypair();
        let (ecdsa_pk, ecdsa_sk) = ecdsa::keypair();
        
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
        
        let mut token = HybridToken {
            claims,
            sig: HybridSig {
                dilithium: String::new(),
                ecdsa_p256: String::new(),
            },
        };
        
        hybrid_sign(&mut token, &dilithium_sk, &ecdsa_sk).unwrap();
        
        let keys = KeyRefs {
            dilithium_pk: &dilithium_pk,
            ecdsa_pk: &ecdsa_pk,
        };
        
        assert!(hybrid_verify(&token, keys).unwrap());
    }

    #[test]
    fn test_verify_token_expired() {
        let (dilithium_pk, dilithium_sk) = pqc::keypair();
        let (ecdsa_pk, ecdsa_sk) = ecdsa::keypair();
        
        let now = Utc::now();
        let claims = Claims {
            v: 2,
            kid: "test".into(),
            iss: "ASTRA".into(),
            sub: "test".into(),
            aud: "sigil-gate".into(),
            iat: now - chrono::Duration::seconds(120),
            nbf: now - chrono::Duration::seconds(120),
            exp: now - chrono::Duration::seconds(60), // Expired 60s ago
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
        
        let mut token = HybridToken {
            claims,
            sig: HybridSig {
                dilithium: String::new(),
                ecdsa_p256: String::new(),
            },
        };
        
        hybrid_sign(&mut token, &dilithium_sk, &ecdsa_sk).unwrap();
        
        let keys = KeyRefs {
            dilithium_pk: &dilithium_pk,
            ecdsa_pk: &ecdsa_pk,
        };
        
        let result = verify_token(&token, keys, None);
        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), SigilError::TokenExpired(_)));
    }
}
