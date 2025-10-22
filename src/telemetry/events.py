import json
import time
import pathlib

LOG = pathlib.Path("logs/events.jsonl")
LOG.parent.mkdir(parents=True, exist_ok=True)

def emit(evt: str, payload: dict):
    rec = {"ts": time.time(), "evt": evt, **payload}
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
