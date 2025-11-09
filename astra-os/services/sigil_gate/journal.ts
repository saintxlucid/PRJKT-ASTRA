import Database from "better-sqlite3";
import crypto from "crypto";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dbPath = path.join(__dirname, "journal.sqlite");
const db = new Database(dbPath);

// Initialize schema with immutability constraints
db.exec(`
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS seals(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL DEFAULT (datetime('now')),
  operator TEXT NOT NULL,
  plan_json TEXT NOT NULL,
  plan_digest TEXT NOT NULL,
  ttl_secs INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS fs_journal(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL DEFAULT (datetime('now')),
  action TEXT NOT NULL,
  path_old TEXT NOT NULL,
  path_new TEXT,
  hash_before TEXT,
  hash_after TEXT,
  undo_script TEXT NOT NULL,
  seal_id INTEGER NOT NULL REFERENCES seals(id)
);

CREATE TABLE IF NOT EXISTS scope_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL DEFAULT (datetime('now')),
  scope_name TEXT NOT NULL,
  action TEXT NOT NULL,
  metadata TEXT
);

CREATE TRIGGER IF NOT EXISTS seals_no_update 
BEFORE UPDATE ON seals 
BEGIN
  SELECT RAISE(ABORT,'immutable: seals');
END;

CREATE TRIGGER IF NOT EXISTS fs_no_update 
BEFORE UPDATE ON fs_journal 
BEGIN
  SELECT RAISE(ABORT,'immutable: fs_journal');
END;
`);

export function digest(plan: unknown): string {
  return crypto.createHash("sha256").update(JSON.stringify(plan)).digest("hex");
}

export function seal(operator: string, plan: unknown, ttl_secs = 600): number {
  const stmt = db.prepare(
    "INSERT INTO seals(ts,operator,plan_json,plan_digest,ttl_secs) VALUES (datetime('now'),?,?,?,?)"
  );
  return stmt.run(operator, JSON.stringify(plan), digest(plan), ttl_secs).lastInsertRowid as number;
}

export function logFsDelete(sealId: number, pathOld: string): void {
  const undo = JSON.stringify({ op: "restore", path: pathOld });
  db.prepare(
    "INSERT INTO fs_journal(ts,action,path_old,path_new,hash_before,hash_after,undo_script,seal_id) VALUES(datetime('now'),'delete',?,NULL,NULL,NULL,?,?)"
  ).run(pathOld, undo, sealId);
}

export function rollbackLast(): boolean {
  const row = db.prepare("SELECT id, undo_script FROM fs_journal ORDER BY id DESC LIMIT 1").get();
  if (!row) return false;
  // Execute real restore later; for now, just remove last entry
  db.prepare("DELETE FROM fs_journal WHERE id=?").run((row as any).id);
  return true;
}

export function latestSeal() {
  return db.prepare("SELECT * FROM seals ORDER BY id DESC LIMIT 1").get();
}
