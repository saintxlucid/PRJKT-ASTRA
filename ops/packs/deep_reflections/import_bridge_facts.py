# ops/packs/deep_reflections/import_bridge_facts.py
import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))

from astra.bridge.memory_bridge import MemoryBridgeService
from astra.bridge.schemas import BridgeFact

facts_path = os.path.join("ops", "packs", "deep_reflections", "bridge_facts.jsonl")
mem = MemoryBridgeService()

batch = []
with open(facts_path, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            data = json.loads(line)
            fact = BridgeFact(**data)
            batch.append(fact)
        if len(batch) >= 100:
            mem.write_facts(batch)
            batch.clear()

if batch:
    mem.write_facts(batch)

print("Imported facts into semantic store.")
