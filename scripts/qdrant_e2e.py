"""Quick Qdrant E2E script for local testing.

- Connects to Qdrant (env QDRANT_URL, default http://127.0.0.1:6333)
- Ensures a small test collection exists (dim=8)
- Upserts 5 random vectors
- Runs a search and prints results
- Appends an `ingestion.complete` event to logs/events.jsonl

Run after starting a local Qdrant instance. This script is intentionally
small and has minimal dependencies (qdrant-client).
"""
import os
import time
import json
import random
from typing import List

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import VectorParams, Distance, PointStruct
except Exception as e:
    raise SystemExit("qdrant-client is required. Install with pip and retry. Error: %s" % e)


QDRANT_URL = os.environ.get("QDRANT_URL", "http://127.0.0.1:6333")
COLLECTION = os.environ.get("QDRANT_COLLECTION", "astra_e2e_test")
DIM = int(os.environ.get("QDRANT_E2E_DIM", "8"))


def random_vector(dim: int) -> List[float]:
    return [random.random() for _ in range(dim)]


def ensure_collection(client: QdrantClient, name: str, dim: int):
    collections = client.get_collections()
    names = [c.name for c in collections.collections]
    if name not in names:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        print(f"Created collection '{name}' (dim={dim})")
    else:
        print(f"Collection '{name}' already exists")


def upsert_sample(client: QdrantClient, name: str, dim: int, count: int = 5):
    points = []
    for i in range(count):
        pid = f"p{i+1}"
        vec = random_vector(dim)
        payload = {"text": f"sample document {i+1}", "meta": {"source": "qdrant_e2e"}}
        points.append(PointStruct(id=pid, vector=vec, payload=payload))

    client.upsert(collection_name=name, points=points)
    print(f"Upserted {len(points)} points to '{name}'")
    return [p.id for p in points]


def search_sample(client: QdrantClient, name: str, query_vec: List[float], k: int = 3):
    results = client.search(collection_name=name, query_vector=query_vec, limit=k)
    print(f"Search returned {len(results)} hits:")
    for r in results:
        print(" - id:", r.id, "score:", getattr(r, "score", None), "payload:", r.payload)
    return results


def emit_event(kind: str, details: dict):
    os.makedirs("logs", exist_ok=True)
    ev = {"ts": int(time.time()), "kind": kind, "details": details}
    with open("logs/events.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(ev) + "\n")
    print("Wrote event to logs/events.jsonl")


def main():
    print("Qdrant E2E: connecting to", QDRANT_URL)
    client = QdrantClient(url=QDRANT_URL)

    ensure_collection(client, COLLECTION, DIM)
    ids = upsert_sample(client, COLLECTION, DIM, count=5)

    # Search using the first vector we inserted (fetch it from the collection via client)
    # For simplicity use a new random vector similar to inserted data distribution
    query = random_vector(DIM)
    results = search_sample(client, COLLECTION, query, k=3)

    emit_event("ingestion.complete", {"collection": COLLECTION, "inserted": len(ids), "results": len(results)})


if __name__ == "__main__":
    main()
