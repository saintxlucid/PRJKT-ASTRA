from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any


def _embed(text: str) -> bytes:
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).digest()


def _bucket_key(vector: bytes, prefix: int = 2) -> str:
    return vector[:prefix].hex()


@dataclass
class Event:
    kind: str
    text: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Concept:
    key: str
    summary: str
    members: list[int] = field(default_factory=list)


class SemanticCompressor:
    """Buckets related events into coarse concepts for fast recall."""

    def __init__(self) -> None:
        self._concepts: dict[str, Concept] = {}
        self._events: list[Event] = []

    def ingest(self, event: Event) -> None:
        vector = _embed(event.text)
        bucket = _bucket_key(vector)
        index = len(self._events)
        self._events.append(event)
        concept = self._concepts.get(bucket)
        if concept is None:
            self._concepts[bucket] = Concept(key=bucket, summary=event.text[:160], members=[index])
            return
        concept.members.append(index)
        if len(event.text) > len(concept.summary):
            concept.summary = event.text[:160]

    def compress(self) -> dict[str, Any]:
        return {
            "concepts": {
                key: {"summary": concept.summary, "members": concept.members}
                for key, concept in self._concepts.items()
            },
            "count_events": len(self._events),
        }

    def rehydrate(self, key: str) -> list[Event]:
        concept = self._concepts.get(key)
        if concept is None:
            return []
        return [self._events[i] for i in concept.members]
