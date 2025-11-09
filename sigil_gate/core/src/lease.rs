use chrono::{DateTime, Utc, Duration};
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use rusqlite::{Connection, params};
use crate::errors::{Result, SigilError};
use crate::DEFAULT_LEASE_DURATION_SECS;

/// Renewable lease for long-running operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Lease {
    pub id: Uuid,
    pub token_kid: String,
    pub created_at: DateTime<Utc>,
    pub expires_at: DateTime<Utc>,
    pub renewed_at: Option<DateTime<Utc>>,
    pub renewal_count: u32,
    pub heartbeat_interval_secs: u64,
    pub last_heartbeat: Option<DateTime<Utc>>,
    pub progress: f32,
    pub state: LeaseState,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum LeaseState {
    Active,
    Expired,
    Revoked,
}

impl Lease {
    /// Create new lease
    pub fn new(token_kid: String, duration_secs: u64, heartbeat_interval_secs: u64) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4(),
            token_kid,
            created_at: now,
            expires_at: now + Duration::seconds(duration_secs as i64),
            renewed_at: None,
            renewal_count: 0,
            heartbeat_interval_secs,
            last_heartbeat: Some(now),
            progress: 0.0,
            state: LeaseState::Active,
        }
    }

    /// Check if lease is expired
    pub fn is_expired(&self, now: DateTime<Utc>) -> bool {
        now > self.expires_at
    }

    /// Check if heartbeat is stale
    pub fn is_heartbeat_stale(&self, now: DateTime<Utc>) -> bool {
        if let Some(last) = self.last_heartbeat {
            let stale_threshold = Duration::seconds((self.heartbeat_interval_secs * 2) as i64);
            now - last > stale_threshold
        } else {
            true
        }
    }

    /// Renew lease
    pub fn renew(&mut self, duration_secs: u64) {
        let now = Utc::now();
        self.expires_at = now + Duration::seconds(duration_secs as i64);
        self.renewed_at = Some(now);
        self.renewal_count += 1;
    }

    /// Update heartbeat
    pub fn heartbeat(&mut self, progress: f32) {
        self.last_heartbeat = Some(Utc::now());
        self.progress = progress.clamp(0.0, 1.0);
    }

    /// Revoke lease
    pub fn revoke(&mut self) {
        self.state = LeaseState::Revoked;
    }
}

/// Lease manager
pub struct LeaseManager {
    conn: Connection,
}

impl LeaseManager {
    /// Open lease manager with SQLite
    pub fn open(db_path: &str) -> Result<Self> {
        let conn = Connection::open(db_path)?;
        conn.execute(
            "CREATE TABLE IF NOT EXISTS leases (
                id TEXT PRIMARY KEY,
                token_kid TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                renewed_at INTEGER,
                renewal_count INTEGER NOT NULL,
                heartbeat_interval_secs INTEGER NOT NULL,
                last_heartbeat INTEGER,
                progress REAL NOT NULL,
                state TEXT NOT NULL
            )",
            [],
        )?;
        Ok(Self { conn })
    }

    /// Create new lease
    pub fn create(&self, token_kid: String, duration_secs: Option<u64>) -> Result<Lease> {
        let duration = duration_secs.unwrap_or(DEFAULT_LEASE_DURATION_SECS);
        let lease = Lease::new(token_kid, duration, DEFAULT_LEASE_DURATION_SECS);
        
        self.conn.execute(
            "INSERT INTO leases (id, token_kid, created_at, expires_at, renewed_at, renewal_count, heartbeat_interval_secs, last_heartbeat, progress, state)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
            params![
                lease.id.to_string(),
                lease.token_kid,
                lease.created_at.timestamp(),
                lease.expires_at.timestamp(),
                lease.renewed_at.map(|t| t.timestamp()),
                lease.renewal_count,
                lease.heartbeat_interval_secs as i64,
                lease.last_heartbeat.map(|t| t.timestamp()),
                lease.progress,
                "Active",
            ],
        )?;
        
        Ok(lease)
    }

    /// Get lease by ID
    pub fn get(&self, id: &Uuid) -> Result<Lease> {
        let mut stmt = self.conn.prepare(
            "SELECT id, token_kid, created_at, expires_at, renewed_at, renewal_count, heartbeat_interval_secs, last_heartbeat, progress, state
             FROM leases WHERE id = ?1"
        )?;

        let lease = stmt.query_row(params![id.to_string()], |row| {
            Ok(Lease {
                id: Uuid::parse_str(&row.get::<_, String>(0)?).unwrap(),
                token_kid: row.get(1)?,
                created_at: DateTime::from_timestamp(row.get(2)?, 0).unwrap(),
                expires_at: DateTime::from_timestamp(row.get(3)?, 0).unwrap(),
                renewed_at: row.get::<_, Option<i64>>(4)?.map(|t| DateTime::from_timestamp(t, 0).unwrap()),
                renewal_count: row.get(5)?,
                heartbeat_interval_secs: row.get::<_, i64>(6)? as u64,
                last_heartbeat: row.get::<_, Option<i64>>(7)?.map(|t| DateTime::from_timestamp(t, 0).unwrap()),
                progress: row.get(8)?,
                state: match row.get::<_, String>(9)?.as_str() {
                    "Active" => LeaseState::Active,
                    "Expired" => LeaseState::Expired,
                    "Revoked" => LeaseState::Revoked,
                    _ => LeaseState::Expired,
                },
            })
        })?;

        Ok(lease)
    }

    /// Renew lease
    pub fn renew(&self, id: &Uuid, duration_secs: Option<u64>) -> Result<()> {
        let mut lease = self.get(id)?;
        
        if lease.state != LeaseState::Active {
            return Err(SigilError::LeaseExpired(format!("Lease {} is {:?}", id, lease.state)));
        }

        let duration = duration_secs.unwrap_or(DEFAULT_LEASE_DURATION_SECS);
        lease.renew(duration);
        
        self.conn.execute(
            "UPDATE leases SET expires_at = ?1, renewed_at = ?2, renewal_count = ?3 WHERE id = ?4",
            params![
                lease.expires_at.timestamp(),
                lease.renewed_at.map(|t| t.timestamp()),
                lease.renewal_count,
                id.to_string(),
            ],
        )?;
        
        Ok(())
    }

    /// Update heartbeat
    pub fn heartbeat(&self, id: &Uuid, progress: f32) -> Result<()> {
        let mut lease = self.get(id)?;
        
        if lease.state != LeaseState::Active {
            return Err(SigilError::LeaseExpired(format!("Lease {} is {:?}", id, lease.state)));
        }
        
        lease.heartbeat(progress);
        
        self.conn.execute(
            "UPDATE leases SET last_heartbeat = ?1, progress = ?2 WHERE id = ?3",
            params![
                lease.last_heartbeat.map(|t| t.timestamp()),
                lease.progress,
                id.to_string(),
            ],
        )?;
        
        Ok(())
    }

    /// Revoke lease
    pub fn revoke(&self, id: &Uuid) -> Result<()> {
        self.conn.execute(
            "UPDATE leases SET state = 'Revoked' WHERE id = ?1",
            params![id.to_string()],
        )?;
        Ok(())
    }

    /// Expire stale leases (run periodically)
    pub fn expire_stale(&self) -> Result<usize> {
        let now = Utc::now();
        let count = self.conn.execute(
            "UPDATE leases SET state = 'Expired' WHERE state = 'Active' AND (expires_at < ?1 OR last_heartbeat < ?2)",
            params![now.timestamp(), (now - Duration::seconds(120)).timestamp()],
        )?;
        Ok(count)
    }

    /// List active leases
    pub fn list_active(&self) -> Result<Vec<Lease>> {
        let mut stmt = self.conn.prepare(
            "SELECT id, token_kid, created_at, expires_at, renewed_at, renewal_count, heartbeat_interval_secs, last_heartbeat, progress, state
             FROM leases WHERE state = 'Active' ORDER BY created_at DESC"
        )?;

        let leases = stmt.query_map([], |row| {
            Ok(Lease {
                id: Uuid::parse_str(&row.get::<_, String>(0)?).unwrap(),
                token_kid: row.get(1)?,
                created_at: DateTime::from_timestamp(row.get(2)?, 0).unwrap(),
                expires_at: DateTime::from_timestamp(row.get(3)?, 0).unwrap(),
                renewed_at: row.get::<_, Option<i64>>(4)?.map(|t| DateTime::from_timestamp(t, 0).unwrap()),
                renewal_count: row.get(5)?,
                heartbeat_interval_secs: row.get::<_, i64>(6)? as u64,
                last_heartbeat: row.get::<_, Option<i64>>(7)?.map(|t| DateTime::from_timestamp(t, 0).unwrap()),
                progress: row.get(8)?,
                state: LeaseState::Active,
            })
        })?
        .collect::<rusqlite::Result<Vec<_>>>()?;

        Ok(leases)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;

    #[test]
    fn test_lease_creation() {
        let lease = Lease::new("test-kid".to_string(), 60, 30);
        assert_eq!(lease.token_kid, "test-kid");
        assert_eq!(lease.state, LeaseState::Active);
        assert!(!lease.is_expired(Utc::now()));
    }

    #[test]
    fn test_lease_renewal() {
        let mut lease = Lease::new("test-kid".to_string(), 1, 30);
        std::thread::sleep(std::time::Duration::from_secs(2));
        assert!(lease.is_expired(Utc::now()));
        
        lease.renew(60);
        assert!(!lease.is_expired(Utc::now()));
        assert_eq!(lease.renewal_count, 1);
    }

    #[test]
    fn test_lease_manager() {
        let temp = NamedTempFile::new().unwrap();
        let manager = LeaseManager::open(temp.path().to_str().unwrap()).unwrap();
        
        let lease = manager.create("test-kid".to_string(), Some(60)).unwrap();
        let retrieved = manager.get(&lease.id).unwrap();
        
        assert_eq!(retrieved.token_kid, "test-kid");
        assert_eq!(retrieved.state, LeaseState::Active);
        
        manager.heartbeat(&lease.id, 0.5).unwrap();
        let updated = manager.get(&lease.id).unwrap();
        assert_eq!(updated.progress, 0.5);
        
        manager.revoke(&lease.id).unwrap();
        let revoked = manager.get(&lease.id).unwrap();
        assert_eq!(revoked.state, LeaseState::Revoked);
    }
}
