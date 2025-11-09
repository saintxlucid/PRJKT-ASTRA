use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use rusqlite::{Connection, params};
use crate::errors::{Result, SigilError};

/// Revocation entry
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Revocation {
    pub rev_id: u64,
    pub token_kid: String,
    pub reason: String,
    pub revoked_at: DateTime<Utc>,
    pub issuer: String,
}

/// Certificate Revocation List (CRL)
pub struct RevocationList {
    conn: Connection,
}

impl RevocationList {
    /// Open revocation list with SQLite
    pub fn open(db_path: &str) -> Result<Self> {
        let conn = Connection::open(db_path)?;
        
        // Create table with append-only constraint
        conn.execute(
            "CREATE TABLE IF NOT EXISTS revocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rev_id INTEGER UNIQUE NOT NULL,
                token_kid TEXT NOT NULL,
                reason TEXT NOT NULL,
                revoked_at INTEGER NOT NULL,
                issuer TEXT NOT NULL,
                CHECK (rev_id > 0)
            )",
            [],
        )?;

        // Immutability triggers
        conn.execute(
            "CREATE TRIGGER IF NOT EXISTS revocations_no_update 
             BEFORE UPDATE ON revocations 
             BEGIN 
                SELECT RAISE(ABORT, 'immutable: revocations'); 
             END",
            [],
        )?;

        conn.execute(
            "CREATE TRIGGER IF NOT EXISTS revocations_no_delete 
             BEFORE DELETE ON revocations 
             BEGIN 
                SELECT RAISE(ABORT, 'immutable: revocations'); 
             END",
            [],
        )?;

        // Index for fast lookups
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rev_id ON revocations(rev_id DESC)",
            [],
        )?;

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_token_kid ON revocations(token_kid)",
            [],
        )?;

        Ok(Self { conn })
    }

    /// Get latest revocation ID
    pub fn latest_rev_id(&self) -> Result<u64> {
        let rev_id: Option<i64> = self.conn.query_row(
            "SELECT MAX(rev_id) FROM revocations",
            [],
            |row| row.get(0),
        )?;
        Ok(rev_id.unwrap_or(0) as u64)
    }

    /// Add revocation (monotonic rev_id)
    pub fn revoke(&self, token_kid: String, reason: String, issuer: String) -> Result<u64> {
        let latest = self.latest_rev_id()?;
        let new_rev_id = latest + 1;
        let now = Utc::now();

        self.conn.execute(
            "INSERT INTO revocations (rev_id, token_kid, reason, revoked_at, issuer)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params![
                new_rev_id as i64,
                token_kid,
                reason,
                now.timestamp(),
                issuer,
            ],
        )?;

        Ok(new_rev_id)
    }

    /// Check if token is revoked
    pub fn is_revoked(&self, token_kid: &str) -> Result<bool> {
        let count: i64 = self.conn.query_row(
            "SELECT COUNT(*) FROM revocations WHERE token_kid = ?1",
            params![token_kid],
            |row| row.get(0),
        )?;
        Ok(count > 0)
    }

    /// Get revocation by token kid
    pub fn get_revocation(&self, token_kid: &str) -> Result<Option<Revocation>> {
        let mut stmt = self.conn.prepare(
            "SELECT rev_id, token_kid, reason, revoked_at, issuer 
             FROM revocations 
             WHERE token_kid = ?1 
             ORDER BY rev_id DESC 
             LIMIT 1"
        )?;

        let result = stmt.query_row(params![token_kid], |row| {
            Ok(Revocation {
                rev_id: row.get::<_, i64>(0)? as u64,
                token_kid: row.get(1)?,
                reason: row.get(2)?,
                revoked_at: DateTime::from_timestamp(row.get(3)?, 0).unwrap(),
                issuer: row.get(4)?,
            })
        });

        match result {
            Ok(rev) => Ok(Some(rev)),
            Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
            Err(e) => Err(e.into()),
        }
    }

    /// List all revocations (for audit)
    pub fn list_all(&self) -> Result<Vec<Revocation>> {
        let mut stmt = self.conn.prepare(
            "SELECT rev_id, token_kid, reason, revoked_at, issuer 
             FROM revocations 
             ORDER BY rev_id DESC"
        )?;

        let revocations = stmt.query_map([], |row| {
            Ok(Revocation {
                rev_id: row.get::<_, i64>(0)? as u64,
                token_kid: row.get(1)?,
                reason: row.get(2)?,
                revoked_at: DateTime::from_timestamp(row.get(3)?, 0).unwrap(),
                issuer: row.get(4)?,
            })
        })?
        .collect::<rusqlite::Result<Vec<_>>>()?;

        Ok(revocations)
    }

    /// Export CRL for distribution
    pub fn export_crl(&self) -> Result<Vec<Revocation>> {
        self.list_all()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;

    #[test]
    fn test_revocation_list() {
        let temp = NamedTempFile::new().unwrap();
        let crl = RevocationList::open(temp.path().to_str().unwrap()).unwrap();

        assert_eq!(crl.latest_rev_id().unwrap(), 0);
        assert!(!crl.is_revoked("test-kid").unwrap());

        let rev_id = crl.revoke("test-kid".to_string(), "test revocation".to_string(), "admin".to_string()).unwrap();
        assert_eq!(rev_id, 1);
        assert!(crl.is_revoked("test-kid").unwrap());

        let revocation = crl.get_revocation("test-kid").unwrap().unwrap();
        assert_eq!(revocation.reason, "test revocation");
        assert_eq!(revocation.issuer, "admin");
    }

    #[test]
    fn test_monotonic_rev_id() {
        let temp = NamedTempFile::new().unwrap();
        let crl = RevocationList::open(temp.path().to_str().unwrap()).unwrap();

        let rev1 = crl.revoke("kid1".to_string(), "reason1".to_string(), "admin".to_string()).unwrap();
        let rev2 = crl.revoke("kid2".to_string(), "reason2".to_string(), "admin".to_string()).unwrap();
        let rev3 = crl.revoke("kid3".to_string(), "reason3".to_string(), "admin".to_string()).unwrap();

        assert_eq!(rev1, 1);
        assert_eq!(rev2, 2);
        assert_eq!(rev3, 3);
        assert_eq!(crl.latest_rev_id().unwrap(), 3);
    }

    #[test]
    #[should_panic(expected = "immutable")]
    fn test_immutability() {
        let temp = NamedTempFile::new().unwrap();
        let crl = RevocationList::open(temp.path().to_str().unwrap()).unwrap();

        crl.revoke("test-kid".to_string(), "test".to_string(), "admin".to_string()).unwrap();

        // This should panic due to immutability trigger
        crl.conn.execute(
            "UPDATE revocations SET reason = 'modified' WHERE token_kid = 'test-kid'",
            [],
        ).unwrap();
    }
}
