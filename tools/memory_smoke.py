import asyncio
import os
import json
import pprint
from astra.memory_engine import MemoryEngine

async def main():
    cfg = {
        "backend": os.environ.get("ASTRA_VECTOR_BACKEND", "auto"),
        "embed_model": os.environ.get("ASTRA_EMBED_MODEL", "all-mpnet-base-v2")
    }
    me = MemoryEngine(cfg)
    print("Connecting memory engine...")
    await me.connect()
    print("Info:", me.info())

    sample_texts = [
        "Cairo nights, the city breathes and the river remembers.",
        "A melody: minor key, four bars, slow reverb — this is a demo of a chorus on 140BPM.",
        "Technical note: implement adapter signing using HMAC-SHA256 and store signature in adapter metadata.",
        "Small poetry: sacred tears, bright fire. The city is a crown of lights."
    ]

    print("\nIngesting sample texts...")
    for i, t in enumerate(sample_texts):
        meta = {
            "author": "test",
            "relevance": 0.9 if i==0 else 0.6,
            "credibility": 0.8,
            "freshness": 0.9,
            "tags": ["demo","smoke"]
        }
        r = me.ingest_text(t, source="smoke_demo", metadata=meta)
        print(" - ingested session:", r.get("session_id"), "chunks:", len(r["chunks"]))

    query = "Cairo city night poetry"
    print("\nRetrieving top results for query:", query)
    res = me.retrieve(query, top_k=5)
    pprint.pprint(res[:5])

    print("\nSampling high-energy items (>=0.7)...")
    high = me.sample_high_energy(min_energy=0.7, limit=20)
    print("High-energy count:", len(high))
    if len(high) >= 2:
        # merge the first two
        a = high[0]["id"]
        b = high[1]["id"]
        print("\nMerging two memories:", a, b)
        merged = me.merge_memories([a, b], reason="smoke-test-merge", note="test merge")
        print("Merged:", merged)
    else:
        print("Not enough high-energy chunks to merge in smoke run.")

    print("\nExport manifest...")
    path = me.export_manifest("./memory_manifest_smoke.json")
    print("Exported to:", path)
    with open(path["path"], "r", encoding="utf-8") as f:
        data = json.load(f)
    print("Manifest items:", len(data.get("items", [])))

if __name__ == "__main__":
    asyncio.run(main())