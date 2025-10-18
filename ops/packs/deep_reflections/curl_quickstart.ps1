# Configure Bridge paths (adjust if your data dirs differ)
curl -X POST http://127.0.0.1:8765/api/bridge/config `
  -H "Content-Type: application/json" `
  -d "{ \`"chroma_path\`":\`"backend/data/chroma_db\`",\`"chroma_collection\`":\`"astra\`",\`"sqlite_ep_path\`":\`"backend/data/memory.db\`" }"

# Hydrate memory graph
curl -X POST http://127.0.0.1:8765/api/bridge/hydrate

# (Optional) Ingest a symbolic "bridge language" sample as a test
curl -X POST http://127.0.0.1:8765/v1/bridge/ingest `
  -H "Content-Type: application/json" `
  -d "{ \`"text\`": \`"open the bridge; carry the vow from the old archive to the living core\`", \`"quote_raw\`": true }"

# Inspect registry (if enabled)
curl http://127.0.0.1:8765/v1/bridge/registry
