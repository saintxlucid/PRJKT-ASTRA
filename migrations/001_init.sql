-- Migration 001: initial schema for Phase 0
-- Creates tables for task checkpoints, conversations and provenance

CREATE TABLE IF NOT EXISTS task_checkpoints (
    task_id TEXT PRIMARY KEY,
    identity TEXT NOT NULL,
    state TEXT NOT NULL,
    data JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_task_checkpoints_updated ON task_checkpoints(updated_at);

CREATE TABLE IF NOT EXISTS conversations (
    identity TEXT PRIMARY KEY,
    messages JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sigil_provenance (
    id SERIAL PRIMARY KEY,
    object_id TEXT,
    sealed_by TEXT,
    seal_hex TEXT,
    meta JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
