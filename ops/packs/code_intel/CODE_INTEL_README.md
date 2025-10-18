# ASTRA Code Intelligence Pack (CIP)

Purpose: Teach ASTRA the full architecture + build, and give her safe, multi-language code read/write.

## Components

- architecture_map.yaml — human-curated system map (modules, responsibilities, data flows)
- build_manifest.yaml — dependencies, build targets, run scripts, ports
- build_facts.jsonl — semantic facts to ingest into LTM (RAG)
- code_languages.yaml — extensions, formatters, LSPs (optional)
- code_memory_schema.sql — SQLite schema for files/symbols/refs/snippets
- code_indexer.py — repo walker + lightweight symbol indexer (+ripgrep optional)
- lsp_bridge.py — optional LSP facade for deep language services
- patch_apply.py — guarded unified-diff/patch applier with allowlist + size caps
- code_routes_stub.py — FastAPI routes: /api/code/*
- code_tools.yaml — Task Agent actions + arg schemas (safe)
- safety_policies.yaml — path allowlist, max lines, timeout
- code_system_prompt.md — coding charter (style, tests, diffs)
- ingest_index.ps1 — one-click index

## Workflow

1. Index → populate code DB
2. Ask → RAG over architecture + symbols
3. Plan → propose patch + tests (dry-run diff)
4. Approve → apply patch (guarded), run tests
5. Learn → store snippets + success outcomes
