"""Utility script to seed a few semantic memories for the Ascension stack."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project sources are importable when launching via `python scripts/seed_memory.py`
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

from astra.infrastructure.storage.vector_store import VectorStore  # type: ignore[import-not-found]
from astra.services.memory_service import MemoryService  # type: ignore[import-not-found]


def main() -> None:
    vector_store = VectorStore(persist_directory="data/chroma")
    memory_service = MemoryService(vector_store)

    memory_service.store_message(
        conversation_id="seed-run",
        role="system",
        content="ASTRA core stack is online and operational.",
    )
    memory_service.store_message(
        conversation_id="seed-run",
        role="user",
        content="Deployment verification completed successfully.",
    )
    memory_service.store_message(
        conversation_id="seed-run",
        role="assistant",
        content="Project Astra history and procedures are indexed for recall.",
    )
    print("Seeded semantic memories into Chroma.")


if __name__ == "__main__":
    main()
