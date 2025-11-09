//! # Sigil Gate Core — Hardened Token System
//! 
//! Post-quantum token system with plan-binding, renewable leases,
//! revocation, and multi-sig approval for hazardous operations.

pub mod token;
pub mod pqc;
pub mod ecdsa;
pub mod verify;
pub mod scopes;
pub mod lease;
pub mod revocation;
pub mod journal;
pub mod env_attest;
pub mod errors;

pub use token::{Claims, HybridToken, HybridSig, Budget, EnvAttestation};
pub use errors::{SigilError, Result};
pub use scopes::{Scope, ScopeKind, ScopeRule};
pub use lease::{Lease, LeaseManager};
pub use revocation::{Revocation, RevocationList};
pub use journal::Journal;

/// Token version (current: 2)
pub const TOKEN_VERSION: u8 = 2;

/// Default lease duration (30 seconds)
pub const DEFAULT_LEASE_DURATION_SECS: u64 = 30;

/// Maximum token expiry (7200 seconds = 2 hours)
pub const MAX_TOKEN_EXPIRY_SECS: u64 = 7200;
