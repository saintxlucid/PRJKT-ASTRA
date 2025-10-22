"""
Document ingestion pipeline for ASTRA
"""
import logging
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from ..core.types import Document
from ..core.embeddings import get_embedder
from ..store.factory import create_store
from ..telemetry.metrics import INGEST_DOCS_COUNTER, INGEST_LATENCY
from ..core.resilience import circuit_breaker, retry_with_backoff

logger = logging.getLogger(__name__)

class IngestionPipeline:
    """Pipeline for ingesting documents into vector store"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.store = create_store(config["index"])
        self.embedder = get_embedder()
        self.events_path = Path("logs/events.jsonl")
        self.events_path.parent.mkdir(exist_ok=True)

    def _log_event(self, event: Dict[str, Any]):
        """Log ingestion event"""
        event["timestamp"] = datetime.utcnow().isoformat()
        with self.events_path.open("a") as f:
            f.write(json.dumps(event) + "\n")

    @circuit_breaker(failure_threshold=5, reset_timeout=30)
    @retry_with_backoff(max_retries=3)
    def ingest(self, documents: List[Document]) -> None:
        """Ingest documents into vector store"""
        with INGEST_LATENCY.time():
            try:
                # Generate embeddings
                for doc in documents:
                    if not doc.embedding:
                        doc.embedding = self.embedder.embed_text(doc.text)

                # Upsert to store
                self.store.upsert(documents)
                
                # Log success
                self._log_event({
                    "type": "ingestion.complete",
                    "num_docs": len(documents)
                })
                
                INGEST_DOCS_COUNTER.inc(len(documents))
                logger.info(f"Successfully ingested {len(documents)} documents")

            except Exception as e:
                logger.error(f"Ingestion failed: {e}")
                self._log_event({
                    "type": "ingestion.error",
                    "error": str(e)
                })
                raise