use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use rusqlite::{Connection, params};
use sha2::{Sha256, Digest};
use crate::errors::Result;

/// Journal entry types
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum JournalAction {
    FsCreate,
    FsDelete,
    FsRename,
    FsMove,
    FsWrite,
    NetConnect,
    NetSend,
    NetResolve,
    ProcSpawn,
    ProcKill,
}

impl JournalAction {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::FsCreate => "create",
            Self::FsDelete => "delete",
            Self::FsRename => "rename",
            Self::FsMove => "move",
            Self::FsWrite => "write",
            Self::NetConnect => "connect",
            Self::NetSend => "send",
            Self::NetResolve => "resolve",
            Self::ProcSpawn => "spawn",
            Self::ProcKill => "kill",
        }
    }
}

/// File system journal entry
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FsJournalEntry {
    pub id: i64,
    pub ts: DateTime<Utc>,
    pub pid: u32,
    pub action: JournalAction,
    pub path_old: String,
    pub path_new: Option<String>,
    pub hash_before: Option<Vec<u8>>,
    pub hash_after: Option<Vec<u8>>,
    pub undo_script: String,
    pub token_id: i64,
    pub prev_hash: Option<Vec<u8>>,
}

/// Network journal entry
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NetJournalEntry {
    pub id: i64,
    pub ts: DateTime<Utc>,
    pub pid: u32,
    pub action: JournalAction,
    pub host: Option<String>,
    pub ip: Option<String>,
    pub port: Option<u16>,
    pub bytes: Option<u64>,
    pub token_id: i64,
}

/// Process journal entry
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcJournalEntry {
    pub id: i64,
    pub ts: DateTime<Utc>,
    pub pid: u32,
    pub action: JournalAction,
    pub cmdline: Option<String>,
    pub parent_pid: Option<u32>,
    pub token_id: i64,
}

/// Audit journal with Merkle chain
pub struct Journal {
    conn: Connection,
}

impl Journal {
    /// Open journal database
    pub fn open(db_path: &str) -> Result<Self> {
        let conn = Connection::open(db_path)?;
        Self::init_schema(&conn)?;
        Ok(Self { conn })
    }

    fn init_schema(conn: &Connection) -> Result<()> {
        // Seals table (token approvals)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS seals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts INTEGER NOT NULL,
                operator TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                token_json TEXT NOT NULL
            )",
            [],
        )?;

        // FS journal with Merkle chain
        conn.execute(
            "CREATE TABLE IF NOT EXISTS journal_fs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts INTEGER NOT NULL,
                pid INTEGER NOT NULL,
                action TEXT NOT NULL,
                path_old TEXT,
                path_new TEXT,
                hash_before BLOB,
                hash_after BLOB,
                undo_script TEXT NOT NULL,
                token_id INTEGER NOT NULL REFERENCES seals(id),
                prev_hash BLOB
            )",
            [],
        )?;

        // Network journal
        conn.execute(
            "CREATE TABLE IF NOT EXISTS journal_net (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts INTEGER NOT NULL,
                pid INTEGER NOT NULL,
                action TEXT NOT NULL,
                host TEXT,
                ip TEXT,
                port INTEGER,
                bytes INTEGER,
                token_id INTEGER NOT NULL REFERENCES seals(id)
            )",
            [],
        )?;

        // Process journal
        conn.execute(
            "CREATE TABLE IF NOT EXISTS journal_proc (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts INTEGER NOT NULL,
                pid INTEGER NOT NULL,
                action TEXT NOT NULL,
                cmdline TEXT,
                parent_pid INTEGER,
                token_id INTEGER NOT NULL REFERENCES seals(id)
            )",
            [],
        )?;

        // Immutability triggers
        for table in &["seals", "journal_fs", "journal_net", "journal_proc"] {
            conn.execute(
                &format!(
                    "CREATE TRIGGER IF NOT EXISTS {}_no_update 
                     BEFORE UPDATE ON {} 
                     BEGIN 
                        SELECT RAISE(ABORT, 'immutable: {}'); 
                     END",
                    table, table, table
                ),
                [],
            )?;

            conn.execute(
                &format!(
                    "CREATE TRIGGER IF NOT EXISTS {}_no_delete 
                     BEFORE DELETE ON {} 
                     BEGIN 
                        SELECT RAISE(ABORT, 'immutable: {}'); 
                     END",
                    table, table, table
                ),
                [],
            )?;
        }

        Ok(())
    }

    /// Record token seal (approval)
    pub fn seal(&self, operator: &str, plan_json: &str, token_json: &str) -> Result<i64> {
        let now = Utc::now();
        self.conn.execute(
            "INSERT INTO seals(ts, operator, plan_json, token_json) VALUES(?1, ?2, ?3, ?4)",
            params![now.timestamp(), operator, plan_json, token_json],
        )?;
        Ok(self.conn.last_insert_rowid())
    }

    /// Get last entry hash from FS journal
    fn get_last_fs_hash(&self) -> Result<Option<Vec<u8>>> {
        let result = self.conn.query_row(
            "SELECT hash_after, prev_hash FROM journal_fs ORDER BY id DESC LIMIT 1",
            [],
            |row| {
                let hash_after: Option<Vec<u8>> = row.get(0)?;
                let prev_hash: Option<Vec<u8>> = row.get(1)?;
                Ok(hash_after.or(prev_hash))
            },
        );

        match result {
            Ok(hash) => Ok(hash),
            Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
            Err(e) => Err(e.into()),
        }
    }

    /// Compute Merkle link hash
    fn compute_merkle_hash(prev_hash: Option<&[u8]>, current_data: &[u8]) -> Vec<u8> {
        let mut hasher = Sha256::new();
        if let Some(prev) = prev_hash {
            hasher.update(prev);
        }
        hasher.update(current_data);
        hasher.finalize().to_vec()
    }

    /// Record FS event
    pub fn fs_event(
        &self,
        pid: u32,
        action: JournalAction,
        path_old: &str,
        path_new: Option<&str>,
        hash_before: Option<&[u8]>,
        hash_after: Option<&[u8]>,
        undo_script: &str,
        token_id: i64,
    ) -> Result<i64> {
        let now = Utc::now();
        let prev_hash = self.get_last_fs_hash()?;

        // Compute Merkle chain link
        let mut data = Vec::new();
        data.extend_from_slice(&now.timestamp().to_le_bytes());
        data.extend_from_slice(&pid.to_le_bytes());
        data.extend_from_slice(path_old.as_bytes());
        if let Some(h) = hash_after {
            data.extend_from_slice(h);
        }

        let merkle_hash = Self::compute_merkle_hash(prev_hash.as_deref(), &data);

        self.conn.execute(
            "INSERT INTO journal_fs(ts, pid, action, path_old, path_new, hash_before, hash_after, undo_script, token_id, prev_hash)
             VALUES(?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
            params![
                now.timestamp(),
                pid,
                action.as_str(),
                path_old,
                path_new,
                hash_before,
                hash_after,
                undo_script,
                token_id,
                prev_hash,
            ],
        )?;

        Ok(self.conn.last_insert_rowid())
    }

    /// Record network event
    pub fn net_event(
        &self,
        pid: u32,
        action: JournalAction,
        host: Option<&str>,
        ip: Option<&str>,
        port: Option<u16>,
        bytes: Option<u64>,
        token_id: i64,
    ) -> Result<i64> {
        let now = Utc::now();
        self.conn.execute(
            "INSERT INTO journal_net(ts, pid, action, host, ip, port, bytes, token_id)
             VALUES(?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            params![now.timestamp(), pid, action.as_str(), host, ip, port.map(|p| p as i64), bytes.map(|b| b as i64), token_id],
        )?;
        Ok(self.conn.last_insert_rowid())
    }

    /// Record process event
    pub fn proc_event(
        &self,
        pid: u32,
        action: JournalAction,
        cmdline: Option<&str>,
        parent_pid: Option<u32>,
        token_id: i64,
    ) -> Result<i64> {
        let now = Utc::now();
        self.conn.execute(
            "INSERT INTO journal_proc(ts, pid, action, cmdline, parent_pid, token_id)
             VALUES(?1, ?2, ?3, ?4, ?5, ?6)",
            params![now.timestamp(), pid, action.as_str(), cmdline, parent_pid, token_id],
        )?;
        Ok(self.conn.last_insert_rowid())
    }

    /// Get FS entries by token ID
    pub fn get_fs_entries_by_token(&self, token_id: i64) -> Result<Vec<FsJournalEntry>> {
        let mut stmt = self.conn.prepare(
            "SELECT id, ts, pid, action, path_old, path_new, hash_before, hash_after, undo_script, token_id, prev_hash
             FROM journal_fs WHERE token_id = ?1 ORDER BY id ASC"
        )?;

        let entries = stmt.query_map(params![token_id], |row| {
            Ok(FsJournalEntry {
                id: row.get(0)?,
                ts: DateTime::from_timestamp(row.get(1)?, 0).unwrap(),
                pid: row.get::<_, i64>(2)? as u32,
                action: match row.get::<_, String>(3)?.as_str() {
                    "create" => JournalAction::FsCreate,
                    "delete" => JournalAction::FsDelete,
                    "rename" => JournalAction::FsRename,
                    "move" => JournalAction::FsMove,
                    "write" => JournalAction::FsWrite,
                    _ => JournalAction::FsWrite,
                },
                path_old: row.get(4)?,
                path_new: row.get(5)?,
                hash_before: row.get(6)?,
                hash_after: row.get(7)?,
                undo_script: row.get(8)?,
                token_id: row.get(9)?,
                prev_hash: row.get(10)?,
            })
        })?
        .collect::<rusqlite::Result<Vec<_>>>()?;

        Ok(entries)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;

    #[test]
    fn test_journal_seal() {
        let temp = NamedTempFile::new().unwrap();
        let journal = Journal::open(temp.path().to_str().unwrap()).unwrap();

        let token_id = journal.seal("admin", r#"{"op":"delete"}"#, r#"{"kid":"test"}"#).unwrap();
        assert_eq!(token_id, 1);
    }

    #[test]
    fn test_fs_journal() {
        let temp = NamedTempFile::new().unwrap();
        let journal = Journal::open(temp.path().to_str().unwrap()).unwrap();

        let token_id = journal.seal("admin", "{}", "{}").unwrap();
        let entry_id = journal.fs_event(
            1234,
            JournalAction::FsDelete,
            "X:/test.txt",
            None,
            Some(&[1, 2, 3]),
            None,
            "touch X:/test.txt",
            token_id,
        ).unwrap();

        assert!(entry_id > 0);

        let entries = journal.get_fs_entries_by_token(token_id).unwrap();
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].path_old, "X:/test.txt");
    }

    #[test]
    fn test_merkle_chain() {
        let temp = NamedTempFile::new().unwrap();
        let journal = Journal::open(temp.path().to_str().unwrap()).unwrap();
        let token_id = journal.seal("admin", "{}", "{}").unwrap();

        journal.fs_event(1234, JournalAction::FsCreate, "file1.txt", None, None, Some(&[1]), "undo1", token_id).unwrap();
        journal.fs_event(1234, JournalAction::FsCreate, "file2.txt", None, None, Some(&[2]), "undo2", token_id).unwrap();

        let entries = journal.get_fs_entries_by_token(token_id).unwrap();
        assert!(entries[1].prev_hash.is_some());
    }
}
