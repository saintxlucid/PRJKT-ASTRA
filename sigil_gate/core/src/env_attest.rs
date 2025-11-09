use chrono::{DateTime, Utc};
use sha2::{Sha256, Digest};
use std::fs;
use std::path::Path;
use crate::token::EnvAttestation;
use crate::errors::{Result, SigilError};

/// Compute SHA-256 hash of a file
pub fn hash_file(path: &Path) -> Result<[u8; 32]> {
    let contents = fs::read(path)
        .map_err(|e| SigilError::EnvAttestationFailed(format!("Cannot read file: {}", e)))?;
    
    let mut hasher = Sha256::new();
    hasher.update(&contents);
    let result = hasher.finalize();
    
    let mut hash = [0u8; 32];
    hash.copy_from_slice(&result);
    Ok(hash)
}

/// Get current process executable path
#[cfg(target_os = "windows")]
pub fn get_current_exe_path() -> Result<std::path::PathBuf> {
    std::env::current_exe()
        .map_err(|e| SigilError::EnvAttestationFailed(format!("Cannot get exe path: {}", e)))
}

#[cfg(target_os = "linux")]
pub fn get_current_exe_path() -> Result<std::path::PathBuf> {
    std::fs::read_link("/proc/self/exe")
        .map_err(|e| SigilError::EnvAttestationFailed(format!("Cannot get exe path: {}", e)))
}

/// Get parent process ID
#[cfg(target_os = "windows")]
pub fn get_parent_pid() -> Result<u32> {
    // Windows: Use NtQueryInformationProcess or similar
    // For now, return stub
    Ok(0)
}

#[cfg(target_os = "linux")]
pub fn get_parent_pid() -> Result<u32> {
    let stat = fs::read_to_string("/proc/self/stat")
        .map_err(|e| SigilError::EnvAttestationFailed(format!("Cannot read /proc/self/stat: {}", e)))?;
    
    let parts: Vec<&str> = stat.split_whitespace().collect();
    if parts.len() > 3 {
        parts[3].parse()
            .map_err(|e| SigilError::EnvAttestationFailed(format!("Cannot parse ppid: {}", e)))
    } else {
        Err(SigilError::EnvAttestationFailed("Invalid /proc/self/stat format".into()))
    }
}

/// Create environment attestation for current process
pub fn create_attestation(cmdline: String) -> Result<EnvAttestation> {
    let exe_path = get_current_exe_path()?;
    let caller_hash = hash_file(&exe_path)?;
    let parent_pid = get_parent_pid()?;
    
    // Job object ID (Windows-specific, stub for now)
    let job_object_id = None; // TODO: Query actual job object on Windows
    
    Ok(EnvAttestation {
        caller_hash,
        cmdline,
        parent_pid,
        job_object_id,
        signed_at: Utc::now(),
    })
}

/// Verify environment attestation
pub fn verify_attestation(attest: &EnvAttestation, expected_hash: &[u8; 32]) -> Result<()> {
    if &attest.caller_hash != expected_hash {
        return Err(SigilError::EnvAttestationFailed(format!(
            "Caller hash mismatch: expected {:?}, got {:?}",
            hex::encode(expected_hash),
            hex::encode(attest.caller_hash)
        )));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    fn test_hash_file() {
        let mut temp = NamedTempFile::new().unwrap();
        temp.write_all(b"test content").unwrap();
        temp.flush().unwrap();
        
        let hash1 = hash_file(temp.path()).unwrap();
        let hash2 = hash_file(temp.path()).unwrap();
        
        assert_eq!(hash1, hash2);
        assert_eq!(hash1.len(), 32);
    }

    #[test]
    fn test_create_attestation() {
        let attest = create_attestation("test command".to_string()).unwrap();
        assert_eq!(attest.cmdline, "test command");
        assert_eq!(attest.caller_hash.len(), 32);
    }
}
