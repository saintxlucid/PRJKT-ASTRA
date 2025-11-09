use clap::{Parser, Subcommand};
use sigil_gate_core::*;
use anyhow::Result;
use chrono::Utc;
use std::collections::BTreeMap;

#[derive(Parser)]
#[command(name = "sigilctl")]
#[command(about = "Sigil Gate CLI - Token management and verification", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Generate new keypair
    Keygen,
    
    /// Create new token
    Create {
        /// Plan JSON file
        #[arg(short, long)]
        plan: String,
        
        /// Scopes (comma-separated)
        #[arg(short, long)]
        scopes: String,
        
        /// Token expiry in seconds
        #[arg(short, long, default_value = "60")]
        expiry: u64,
    },
    
    /// Verify token
    Verify {
        /// Token JSON file
        #[arg(short, long)]
        token: String,
    },
    
    /// Revoke token
    Revoke {
        /// Token KID
        #[arg(short, long)]
        kid: String,
        
        /// Reason
        #[arg(short, long)]
        reason: String,
        
        /// CRL database path
        #[arg(long, default_value = "crl.db")]
        crl_db: String,
    },
    
    /// List revocations
    ListRevocations {
        /// CRL database path
        #[arg(long, default_value = "crl.db")]
        crl_db: String,
    },
    
    /// Create lease
    CreateLease {
        /// Token KID
        #[arg(short, long)]
        kid: String,
        
        /// Duration in seconds
        #[arg(short, long, default_value = "30")]
        duration: u64,
        
        /// Lease database path
        #[arg(long, default_value = "leases.db")]
        lease_db: String,
    },
    
    /// List active leases
    ListLeases {
        /// Lease database path
        #[arg(long, default_value = "leases.db")]
        lease_db: String,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Keygen => {
            println!("Generating hybrid keypair (Dilithium2 + ECDSA P-256)...");
            let (dilithium_pk, _dilithium_sk) = pqc::keypair();
            let (ecdsa_pk, _ecdsa_sk) = ecdsa::keypair();
            
            println!("\n✅ Keypair generated successfully!");
            println!("\nDilithium2 Public Key (base64):");
            println!("{}", pqc::pub_key_to_base64(&dilithium_pk));
            println!("\nECDSA P-256 Public Key (DER hex):");
            println!("{}", hex::encode(ecdsa_pk.to_encoded_point(false).as_bytes()));
            println!("\n⚠️  Private keys NOT shown (store securely)");
        }
        
        Commands::Create { plan, scopes, expiry } => {
            println!("Creating token...");
            
            // Read plan
            let plan_json = std::fs::read_to_string(&plan)?;
            let plan_digest = Claims::compute_plan_digest(&plan_json);
            
            // Parse scopes
            let scope_list: Vec<String> = scopes.split(',').map(|s| s.trim().to_string()).collect();
            
            // Generate keys (in production, load from secure storage)
            let (dilithium_pk, dilithium_sk) = pqc::keypair();
            let (ecdsa_pk, ecdsa_sk) = ecdsa::keypair();
            
            // Create attestation
            let env_attest = env_attest::create_attestation(
                std::env::args().collect::<Vec<_>>().join(" ")
            )?;
            
            let now = Utc::now();
            let claims = Claims {
                v: TOKEN_VERSION,
                kid: format!("sigil-{}", uuid::Uuid::new_v4()),
                iss: "ASTRA".into(),
                sub: format!("proc:{}", std::process::id()),
                aud: "sigil-gate".into(),
                iat: now,
                nbf: now,
                exp: now + chrono::Duration::seconds(expiry as i64),
                nonce: uuid::Uuid::new_v4().to_string(),
                scopes: scope_list,
                budget: Budget::default(),
                plan_digest,
                env_attest,
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
            
            verify::hybrid_sign(&mut token, &dilithium_sk, &ecdsa_sk)?;
            
            let token_json = token.to_json()?;
            let token_file = format!("token-{}.json", token.claims.kid);
            std::fs::write(&token_file, &token_json)?;
            
            println!("\n✅ Token created: {}", token_file);
            println!("\nKID: {}", token.claims.kid);
            println!("Expires: {}", token.claims.exp);
            println!("Scopes: {:?}", token.claims.scopes);
        }
        
        Commands::Verify { token } => {
            println!("Verifying token...");
            
            let token_json = std::fs::read_to_string(&token)?;
            let token = HybridToken::from_json(&token_json)?;
            
            // Generate keys (in production, load public keys)
            let (dilithium_pk, _) = pqc::keypair();
            let (ecdsa_pk, _) = ecdsa::keypair();
            
            let keys = verify::KeyRefs {
                dilithium_pk: &dilithium_pk,
                ecdsa_pk: &ecdsa_pk,
            };
            
            match verify::verify_token(&token, keys, None) {
                Ok(_) => {
                    println!("\n✅ Token is VALID");
                    println!("\nKID: {}", token.claims.kid);
                    println!("Subject: {}", token.claims.sub);
                    println!("Expires: {}", token.claims.exp);
                }
                Err(e) => {
                    println!("\n❌ Token is INVALID: {}", e);
                }
            }
        }
        
        Commands::Revoke { kid, reason, crl_db } => {
            println!("Revoking token {}...", kid);
            
            let crl = RevocationList::open(&crl_db)?;
            let rev_id = crl.revoke(kid.clone(), reason.clone(), "admin".into())?;
            
            println!("\n✅ Token revoked");
            println!("Revocation ID: {}", rev_id);
            println!("Reason: {}", reason);
        }
        
        Commands::ListRevocations { crl_db } => {
            let crl = RevocationList::open(&crl_db)?;
            let revocations = crl.list_all()?;
            
            if revocations.is_empty() {
                println!("No revocations found.");
            } else {
                println!("\n📋 Revocations:\n");
                for rev in revocations {
                    println!("ID: {} | KID: {} | Revoked: {} | Reason: {}",
                        rev.rev_id, rev.token_kid, rev.revoked_at, rev.reason);
                }
            }
        }
        
        Commands::CreateLease { kid, duration, lease_db } => {
            println!("Creating lease for token {}...", kid);
            
            let manager = LeaseManager::open(&lease_db)?;
            let lease = manager.create(kid, Some(duration))?;
            
            println!("\n✅ Lease created");
            println!("Lease ID: {}", lease.id);
            println!("Expires: {}", lease.expires_at);
        }
        
        Commands::ListLeases { lease_db } => {
            let manager = LeaseManager::open(&lease_db)?;
            let leases = manager.list_active()?;
            
            if leases.is_empty() {
                println!("No active leases found.");
            } else {
                println!("\n📋 Active Leases:\n");
                for lease in leases {
                    println!("ID: {} | KID: {} | Expires: {} | Progress: {:.0}%",
                        lease.id, lease.token_kid, lease.expires_at, lease.progress * 100.0);
                }
            }
        }
    }

    Ok(())
}
