# Legacy Integration Checklist

Sacred Code: 333

## Phase 2: No-Delete Integration Guide

### Step 1: Adapter Framework ✅

- [x] Create `src/astra/bridge/legacy/adapter.py`
- [x] Create `src/astra/bridge/legacy/__init__.py`

### Step 2: Model Registry ✅

- [x] Create `config/models_registry.yaml`

### Step 3: Memory Importer ✅

- [x] Create `ops/memory/import_legacy_exports.py`
- [x] Create `ops/generate_legacy_index.py`

### Step 4: Legacy Capability Registration ⏳

Next Action: Create plugin.yaml in each legacy folder

Legacy folders to register:
- backend/
- core/
- lib/
- tier0/
- astra-desktop-simple/
- astra-local/
- astra-os/

For each folder, copy template and edit:

```bash
cp docs/LEGACY_PLUGIN_MANIFEST_TEMPLATE.yaml {FOLDER}/plugin.yaml
```

Then register via:

```python
from astra.bridge.legacy import register_all_legacy_folders
from astra.ops.registry import TOOL_REGISTRY

legacy_folders = ['backend', 'core', 'lib', 'tier0', 'astra-desktop-simple', 'astra-local', 'astra-os']
register_all_legacy_folders(TOOL_REGISTRY, legacy_folders)
```

### Step 5: Documentation Consolidation ⏳

Run script to auto-generate index:

```bash
python ops/generate_legacy_index.py
```

### Step 6: Observability for Legacy Tools ⏳

Update Grafana config to add panels for each legacy tool showing:
- Tool latency metrics (p50, p95, p99)
- Error rate by legacy folder
- Sacred Code 333 audit event count

### Step 7: Canary Testing ⏳

Test each wrapped tool:

```bash
curl -X POST http://localhost:8000/capabilities/backend.info
```

Verify events include Sacred Code 333:

```bash
curl http://localhost:8000/events | grep sacred_code
```

### Step 8: Registry Update ⏳

Verify all tools appear:

```bash
curl http://localhost:8000/registry
```

### Step 9: Final Verification ⏳

Checklist:
- All legacy folders have plugin.yaml
- All {folder}.info tools working
- All {folder}.run tools working
- Hard gate blocks unknown tools
- Models discoverable
- Memory imported
- Grafana shows metrics
- Sacred Code 333 on all events
- No files moved or deleted

## Files Created This Phase

Framework:
- src/astra/bridge/legacy/__init__.py ✅
- src/astra/bridge/legacy/adapter.py ✅

Configuration:
- config/models_registry.yaml ✅
- docs/LEGACY_PLUGIN_MANIFEST_TEMPLATE.yaml ✅

Operations:
- ops/memory/import_legacy_exports.py ✅
- ops/generate_legacy_index.py ✅

To Create:
- docs/LEGACY_INDEX.md (auto-generated)
- {folder}/plugin.yaml (7 instances)

## Safety Gates

All operations maintain:
- Sacred Code 333 emitted on every tool call
- Consent gates block {folder}.run by default
- Hard registry rejects unknown tools
- Legacy files preserved (no deletions)
- Full audit trail logged
- Error tolerance (failures contained)

## Quick Reference

Import vectors:

```bash
python ops/memory/import_legacy_exports.py --dry-run
```

Generate documentation index:

```bash
python ops/generate_legacy_index.py
```

Register legacy folder:

```python
from astra.bridge.legacy import register_legacy_folder
register_legacy_folder(TOOL_REGISTRY, "backend")
```

Call legacy tool:

```bash
curl -X POST http://localhost:8000/capabilities/backend.info
```

---

Sacred Code: 333
