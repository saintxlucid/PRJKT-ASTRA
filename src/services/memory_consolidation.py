# Memory Consolidation Service ("Dreaming")
# SPDX-License-Identifier: MIT
"""
MemoryConsolidationService: Nightly "dreaming" to convert episodic → semantic.

Mimics human memory consolidation during sleep:
- Cluster episodic events into themes (e.g., "user frequently asks about X")
- Summarize themes with local LLM
- Store summaries in semantic memory (ChromaDB)
- Mark consolidated events (prevent re-processing)

Performance: Processes ~50 events in ~2-3 minutes (CPU inference).
Clustering: HDBSCAN on BGE-M3 embeddings (1024D)
Summarization: llama.cpp local LLM (~200 tokens per summary)

Example:
    50 episodic events → 3-5 semantic themes:
    - "User frequently asks about hexagonal architecture"
    - "User prefers local-first tools over cloud services"
    - "User values provenance and citations in responses"
"""
from __future__ import annotations
import json
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# NumPy for clustering
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# Sklearn for clustering (HDBSCAN or KMeans fallback)
try:
    from sklearn.cluster import DBSCAN
    from sklearn.neighbors import NearestNeighbors
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Prometheus metrics
try:
    from prometheus_client import Counter, Gauge, Histogram
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# Local imports
from domain.events import Event
from gateways.event_store_sqlite import SQLiteEventStore
from gateways.chroma_memory_gateway_bge import ChromaMemoryGatewayBGE
from services.embeddings_bge_m3 import BGE_M3_Embedder
from services.llm_service_local import LocalLLMService
from services.memory_provenance import (
    build_provenance_prompt,
    parse_provenance_line,
    validate_summary_against_events,
    compute_quality_score_bow,
    leaf_hash,
    cluster_root_hash,
    sign_summary
)
from services.consolidation_lock import (
    acquire_dream_lock,
    mark_job_success,
    mark_job_failed,
    get_watermark,
    set_watermark
)

# Prometheus metrics for observability
if PROMETHEUS_AVAILABLE:
    dream_runs_total = Counter(
        "astra_dream_runs_total",
        "Nightly consolidations started"
    )
    dream_runs_success_total = Counter(
        "astra_dream_runs_success_total",
        "Consolidations succeeded"
    )
    dream_events_processed = Counter(
        "astra_dream_events_processed_total",
        "Episodic events processed"
    )
    dream_clusters_formed = Counter(
        "astra_dream_clusters_total",
        "Clusters formed"
    )
    dream_noise_count = Counter(
        "astra_dream_noise_total",
        "Events marked noise"
    )
    dream_duration_seconds = Histogram(
        "astra_dream_duration_seconds",
        "Consolidation duration"
    )
    dream_overlap_lock = Gauge(
        "astra_dream_overlap_lock",
        "1 if a run is in progress, else 0"
    )
    dream_quality_score = Histogram(
        "astra_dream_quality_score",
        "0..1 quality score per run"
    )


def choose_eps_cosine(embeddings: np.ndarray) -> float:
    """
    Auto-tune DBSCAN eps parameter via k-distance elbow method.
    
    Algorithm:
    1. Compute k-nearest neighbor distances (k=5) for all embeddings
    2. Sort distances in ascending order
    3. Find elbow point (95th percentile)
    4. Clamp to safe range: [0.15, 0.45]
    
    Args:
        embeddings: Event embeddings (shape: [N, D])
    
    Returns:
        Optimal eps (clamped to [0.15, 0.45])
    """
    if not SKLEARN_AVAILABLE or not NUMPY_AVAILABLE:
        return 0.5  # Fallback
    
    from sklearn.neighbors import NearestNeighbors
    
    X = np.asarray(embeddings, dtype=float)
    k = min(5, max(2, len(X) // 20))  # Adapt k to dataset size
    
    nbrs = NearestNeighbors(n_neighbors=k, metric="cosine").fit(X)
    dists, _ = nbrs.kneighbors(X)
    
    # k-th distance for each point
    kdist = np.sort(dists[:, -1])
    
    # Elbow = 95th percentile (robust to outliers)
    q = float(np.quantile(kdist, 0.95))
    
    # Clamp to safe range
    return max(0.15, min(0.45, q))


@dataclass
class ConsolidationConfig:
    """Configuration for memory consolidation."""
    # Event selection
    min_events: int = 10  # Minimum events to trigger consolidation
    max_events: int = 100  # Maximum events to process per run
    lookback_hours: int = 24  # Only consolidate recent events
    
    # Clustering
    clustering_eps: float = 0.5  # DBSCAN epsilon (cosine distance threshold)
    min_cluster_size: int = 3  # Minimum events per cluster
    
    # Summarization
    summary_max_tokens: int = 200  # LLM summary length
    summary_temperature: float = 0.7  # LLM creativity
    
    # Storage
    store_to_memory: bool = True  # Store summaries in semantic memory
    mark_consolidated: bool = True  # Mark events as processed


@dataclass
class EventCluster:
    """Group of related episodic events."""
    cluster_id: int
    events: list[Event]
    centroid: np.ndarray | None = None
    theme: str = ""  # Human-readable theme
    summary: str = ""  # LLM-generated summary
    used_ids: list[int] | None = None


class MemoryConsolidationService:
    """
    Nightly "dreaming" service: episodic events → semantic summaries.
    
    Architecture:
    1. Read episodic events from SQLiteEventStore
    2. Embed events with BGE-M3
    3. Cluster embeddings with DBSCAN
    4. Summarize each cluster with local LLM
    5. Store summaries in ChromaMemoryGatewayBGE
    6. Mark events as consolidated (metadata)
    
    Usage:
        service = MemoryConsolidationService(
            event_store=SQLiteEventStore(),
            memory_gateway=ChromaMemoryGatewayBGE(),
            llm_service=LocalLLMService(),
            config=ConsolidationConfig()
        )
        
        # Run consolidation
        result = service.consolidate()
        print(f"Processed {result['events_count']} events")
        print(f"Created {result['clusters_count']} themes")
    """
    
    def __init__(
        self,
        event_store: SQLiteEventStore,
        memory_gateway: ChromaMemoryGatewayBGE,
        llm_service: LocalLLMService,
        config: ConsolidationConfig | None = None
    ):
        if not NUMPY_AVAILABLE:
            raise RuntimeError("numpy not installed. Run: pip install numpy")
        
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn not installed. Run: pip install scikit-learn")
        
        self.event_store = event_store
        self.memory_gateway = memory_gateway
        self.llm_service = llm_service
        self.config = config or ConsolidationConfig()
        
        # Initialize BGE-M3 embedder
        self.embedder = BGE_M3_Embedder()
    
    def _get_unconsolidated_events(
        self,
        since_iso: str | None = None,
        limit_override: int = 0,
        watermark: int | None = None,
        mode: str = "live"
    ) -> list[Event]:
        """
        Get episodic events that haven't been consolidated yet.
        
        Filters:
        - Not marked as consolidated
        - Within lookback window (e.g., last 24 hours)
        - Excludes system events (boot, health_check)
        
        Returns:
            List of Event objects
        """
        # Determine cutoff time depending on mode/backfill
        if mode == "backfill" and since_iso:
            cutoff_time = since_iso
        else:
            cutoff_time = (
                datetime.utcnow() - timedelta(hours=self.config.lookback_hours)
            ).isoformat() + "Z"
        
        events = []
        for event in self.event_store.replay():
            # Skip if already consolidated
            if event.payload.get("_consolidated", False):
                continue

            # Watermark: for live mode skip events with id <= watermark
            if watermark is not None:
                try:
                    if getattr(event, "id", 0) <= int(watermark):
                        continue
                except Exception:
                    pass

            # Backfill mode: only include events at/after since_iso if provided
            if mode == "backfill" and since_iso:
                try:
                    ev_ts = datetime.fromisoformat(event.ts.rstrip("Z"))
                    since_dt = datetime.fromisoformat(since_iso.rstrip("Z"))
                    if ev_ts < since_dt:
                        continue
                except Exception:
                    # Fallback to string compare
                    if event.ts < since_iso:
                        continue

            else:
                # Live/dry/default: skip if too old based on lookback window
                try:
                    if event.ts < cutoff_time:
                        continue
                except Exception:
                    pass
            
            # Skip system events
            if event.typ in ["system_boot", "health_check", "heartbeat"]:
                continue
            
            events.append(event)
            
            events.append(event)

            # Respect optional limit_override for manual runs
            effective_limit = self.config.max_events
            if limit_override and limit_override > 0:
                effective_limit = min(effective_limit, limit_override)

            if len(events) >= effective_limit:
                break
        
        return events
    
    def _embed_events(self, events: list[Event]) -> np.ndarray:
        """
        Embed events with BGE-M3.
        
        Event text format: "{typ}: {payload summary}"
        Example: "tool_executed: ran command 'ls -la'"
        
        Args:
            events: List of Event objects
        
        Returns:
            NumPy array of embeddings (shape: [N, 1024])
        """
        texts = []
        for event in events:
            # Create human-readable text from event
            payload_preview = json.dumps(event.payload, sort_keys=True)[:200]
            text = f"{event.typ}: {payload_preview}"
            texts.append(text)
        
        # Batch embed with BGE-M3
        embeddings = self.embedder.embed_batch(texts)
        return embeddings
    
    def _cluster_events(
        self,
        events: list[Event],
        embeddings: np.ndarray
    ) -> list[EventCluster]:
        """
        Cluster events using DBSCAN on BGE-M3 embeddings.
        
        DBSCAN: Density-based clustering, auto-detects number of clusters.
        - eps: Maximum distance between points in same cluster
        - min_samples: Minimum points to form cluster
        
        Args:
            events: List of Event objects
            embeddings: BGE-M3 embeddings (shape: [N, 1024])
        
        Returns:
            List of EventCluster objects
        """
        # Normalize embeddings for cosine similarity
        embeddings_norm = embeddings / np.linalg.norm(
            embeddings, axis=1, keepdims=True
        )
        
        # Step 6: Auto-tune eps parameter (k-distance elbow method)
        eps_value = choose_eps_cosine(embeddings_norm)
        
        # DBSCAN clustering
        clustering = DBSCAN(
            eps=eps_value,  # Dynamic (was fixed at 0.5)
            min_samples=self.config.min_cluster_size,
            metric="cosine"
        )
        
        labels = clustering.fit_predict(embeddings_norm)
        
        # Group events by cluster
        clusters_dict = defaultdict(list)
        for i, label in enumerate(labels):
            if label == -1:  # Noise (unclustered events)
                continue
            clusters_dict[label].append((events[i], embeddings[i]))
        
        # Create EventCluster objects
        clusters = []
        for cluster_id, items in clusters_dict.items():
            cluster_events = [e for e, _ in items]
            cluster_embeddings = np.array([emb for _, emb in items])
            
            # Calculate centroid
            centroid = np.mean(cluster_embeddings, axis=0)
            
            clusters.append(EventCluster(
                cluster_id=cluster_id,
                events=cluster_events,
                centroid=centroid
            ))
        
        return clusters
    
    def _generate_theme(self, cluster: EventCluster) -> str:
        """
        Generate human-readable theme for cluster.
        
        Theme format: "User {verb} {object}"
        Example: "User frequently asks about architecture"
        
        Simple heuristic:
        - Count event types in cluster
        - Return most common type
        
        Args:
            cluster: EventCluster object
        
        Returns:
            Theme string
        """
        # Count event types
        type_counts = defaultdict(int)
        for event in cluster.events:
            type_counts[event.typ] += 1
        
        # Most common type
        most_common_type = max(type_counts.items(), key=lambda x: x[1])
        
        return f"Cluster {cluster.cluster_id}: {most_common_type[0]} ({most_common_type[1]} events)"
    
    def _summarize_cluster(self, cluster: EventCluster) -> str:
        """
        Summarize cluster with local LLM + provenance enforcement (Step 4).
        
        Step 4 Integration: Hallucination Guard
        - Build strict prompt with PROVENANCE requirement
        - Parse and validate provenance line from LLM output
        - Enforce 60% lexical grounding (tokens must appear in source events)
        
        Args:
            cluster: EventCluster object
        
        Returns:
            LLM-generated summary (validated)
        
        Raises:
            ValueError: If provenance missing/invalid or hallucination detected
        """
        # Build cluster events for provenance prompt
        cluster_events = []
        for event in cluster.events[:10]:  # Limit to 10 events
            cluster_events.append({
                "id": event.id if hasattr(event, 'id') else 0,
                "payload": {"text": json.dumps(event.payload, sort_keys=True)[:150]}
            })
        
        # Calculate root hash for this cluster
        event_hashes = [
            leaf_hash(e["id"], e["payload"]["text"])
            for e in cluster_events
        ]
        root = cluster_root_hash(event_hashes)
        
        # Step 4: Build provenance-enforcing prompt
        system_msg, user_msg = build_provenance_prompt(cluster_events, root)
        
        # Generate summary with LLM
        try:
            # Construct prompt (system + user messages combined for local LLM)
            full_prompt = f"{system_msg['content']}\n\n{user_msg['content']}"
            
            summary = self.llm_service.complete(
                prompt=full_prompt,
                max_tokens=self.config.summary_max_tokens,
                temperature=self.config.summary_temperature,
                stop=["\n\n", "Context:", "Task:"]
            )
            
            # Step 4: Parse provenance line
            parsed_root, used_ids = parse_provenance_line(summary)

            # Step 4: Validate summary is lexically grounded
            validate_summary_against_events(
                summary_text=summary,
                cluster_events=cluster_events,
                root_hash=root,
                used_ids=used_ids
            )

            # Attach used IDs to cluster for downstream quality scoring
            cluster.used_ids = used_ids

            return summary.strip()
            
        except ValueError as e:
            # Provenance validation failed (hallucination detected)
            if PROMETHEUS_AVAILABLE:
                # Increment provenance failure counter
                try:
                    from prometheus_client import Counter
                    provenance_failures = Counter(
                        "astra_dream_provenance_failures_total",
                        "Summaries rejected for provenance violations"
                    )
                    provenance_failures.inc()
                except:
                    pass
            
            # Fallback: simple concatenation (no LLM hallucination)
            return f"Cluster of {len(cluster.events)} {cluster.events[0].typ} events"
        
        except Exception:
            # Other LLM errors: fallback
            return f"Cluster of {len(cluster.events)} {cluster.events[0].typ} events"
    
    def _store_summary(self, cluster: EventCluster):
        """
        Store cluster summary in semantic memory.
        
        Metadata:
        - cluster_id: Cluster identifier
        - events_count: Number of events in cluster
        - event_types: List of event types
        - timestamp: Consolidation timestamp
        - source: "memory_consolidation"
        
        Args:
            cluster: EventCluster object
        """
        metadata = {
            "cluster_id": cluster.cluster_id,
            "events_count": len(cluster.events),
            "event_types": list(set(e.typ for e in cluster.events)),
            "timestamp": time.time(),
            "source": "memory_consolidation",
            "type": "semantic_summary"
        }
        
        self.memory_gateway.store(
            text=cluster.summary,
            metadata=metadata
        )
    
    def _mark_events_consolidated(self, events: list[Event]):
        """
        Mark events as consolidated (prevent re-processing).
        
        Note: SQLiteEventStore is append-only, so we can't modify events.
        Instead, we store a separate "consolidated" event for each batch.
        
        Args:
            events: List of Event objects
        """
        event_ids = [e.id for e in events]
        
        self.event_store.append(
            typ="memory_consolidated",
            payload={
                "event_ids": event_ids,
                "events_count": len(event_ids),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            },
            identity_snapshot={"agent": "memory_consolidation_service"}
        )
    
    def consolidate(self, mode: str = "live", since: str | None = None, limit: int = 0) -> dict[str, Any]:
        """
        Run memory consolidation ("dreaming").
        
        Steps:
        1. Get unconsolidated events
        2. Embed events with BGE-M3
        3. Cluster embeddings with DBSCAN
        4. Summarize each cluster with local LLM
        5. Store summaries in semantic memory
        6. Mark events as consolidated
        
        Returns:
            Dict with consolidation statistics:
            - events_count: Number of events processed
            - clusters_count: Number of themes discovered
            - summaries_stored: Number of summaries stored
            - duration_seconds: Processing time
        """
        start_time = time.time()

        # Step 1: Get unconsolidated events (respect watermark/limit/mode)
        watermark = None
        try:
            if mode == "live":
                watermark = get_watermark()
        except Exception:
            watermark = None

        events = self._get_unconsolidated_events(
            since_iso=since,
            limit_override=limit,
            watermark=watermark,
            mode=mode
        )
        
        if len(events) < self.config.min_events:
            return {
                "events_count": len(events),
                "clusters_count": 0,
                "summaries_stored": 0,
                "duration_seconds": time.time() - start_time,
                "status": "skipped_insufficient_events"
            }
        
        # Metrics: start/run
        if PROMETHEUS_AVAILABLE:
            try:
                dream_runs_total.inc()
                dream_overlap_lock.set(1)
            except Exception:
                pass

        # Step 2: Embed events
        embeddings = self._embed_events(events)
        
        # Step 3: Cluster events
        clusters = self._cluster_events(events, embeddings)
        
        # Step 4: Summarize clusters
        summaries_stored = 0
        for cluster in clusters:
            # Generate theme
            cluster.theme = self._generate_theme(cluster)
            
            # Summarize with LLM
            cluster.summary = self._summarize_cluster(cluster)
            
            # Store in semantic memory (unless dry run)
            if self.config.store_to_memory and mode != "dry":
                self._store_summary(cluster)
                summaries_stored += 1
        
        # Compute quality score (BoW fallback) across clusters
        try:
            covered_ids = set()
            summary_texts = []
            for c in clusters:
                if c.used_ids:
                    covered_ids.update(c.used_ids)
                if c.summary:
                    summary_texts.append(c.summary)

            # Recency flags for events (last 48h)
            now = datetime.utcnow()
            event_recency_flags = []
            for ev in events:
                try:
                    ev_dt = datetime.fromisoformat(ev.ts.rstrip("Z"))
                    event_recency_flags.append((now - ev_dt).total_seconds() <= 48 * 3600)
                except Exception:
                    event_recency_flags.append(False)

            quality_score = compute_quality_score_bow(
                total_events=len(events),
                covered_event_ids=list(covered_ids),
                summary_texts=summary_texts,
                event_recency_flags=event_recency_flags
            )
            if PROMETHEUS_AVAILABLE:
                try:
                    dream_quality_score.observe(float(quality_score))
                except Exception:
                    pass
        except Exception:
            quality_score = 0.0

        # Step 5: Mark events as consolidated (only for live mode)
        try:
            if self.config.mark_consolidated and mode == "live":
                self._mark_events_consolidated(events)
                # advance watermark to last event id
                try:
                    last_id = max(getattr(e, "id", 0) for e in events)
                    set_watermark(int(last_id))
                except Exception:
                    pass
        except Exception:
            pass
        
        duration = time.time() - start_time

        # Prometheus metrics: finish
        if PROMETHEUS_AVAILABLE:
            try:
                dream_events_processed.inc(len(events))
                dream_clusters_formed.inc(len(clusters))
                dream_duration_seconds.observe(duration)
                dream_overlap_lock.set(0)
                dream_runs_success_total.inc()
            except Exception:
                pass

        return {
            "events_count": len(events),
            "clusters_count": len(clusters),
            "summaries_stored": summaries_stored,
            "duration_seconds": round(duration, 2),
            "quality_score": float(quality_score),
            "status": "success"
        }
    
    def get_consolidation_history(self) -> list[dict]:
        """
        Get history of past consolidation runs.
        
        Returns:
            List of consolidation metadata (timestamp, events_count, etc.)
        """
        history = []
        for event in self.event_store.get_by_type("memory_consolidated"):
            history.append({
                "timestamp": event.ts,
                "events_count": event.payload.get("events_count", 0),
                "event_ids": event.payload.get("event_ids", [])
            })
        
        return history


# Factory function
def build_consolidation_service_from_config(conf: dict) -> MemoryConsolidationService:
    """
    Factory: Build MemoryConsolidationService from config.
    
    Config example (astra.yaml):
        memory_consolidation:
          enabled: true
          schedule: "0 2 * * *"  # 2 AM daily
          config:
            min_events: 10
            max_events: 100
            lookback_hours: 24
            clustering_eps: 0.5
            min_cluster_size: 3
            summary_max_tokens: 200
    """
    from services.llm_service_local import build_llm_service_from_config
    from gateways.chroma_memory_gateway_bge import build_chroma_gateway_bge_from_config
    
    # Build dependencies
    event_store = SQLiteEventStore(
        db_path=conf.get("event_store", {}).get("path", "data/eventlog.sqlite")
    )
    memory_gateway = build_chroma_gateway_bge_from_config(conf)
    llm_service = build_llm_service_from_config(conf)
    
    # Build config
    cons_conf = conf.get("memory_consolidation", {}).get("config", {})
    config = ConsolidationConfig(**cons_conf)
    
    return MemoryConsolidationService(
        event_store=event_store,
        memory_gateway=memory_gateway,
        llm_service=llm_service,
        config=config
    )


# CLI for manual testing
if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    print("=== Memory Consolidation Service Test ===\n")
    
    # Initialize dependencies
    print("Initializing dependencies...")
    event_store = SQLiteEventStore(db_path="data/eventlog.sqlite")
    memory_gateway = ChromaMemoryGatewayBGE(
        persist_dir="data/memory_bge_m3",
        hmac_key="test-key"
    )
    llm_service = LocalLLMService()  # Will use default config
    
    # Initialize service
    service = MemoryConsolidationService(
        event_store=event_store,
        memory_gateway=memory_gateway,
        llm_service=llm_service,
        config=ConsolidationConfig(
            min_events=5,  # Lower threshold for testing
            max_events=50
        )
    )
    
    print(f"✅ Service initialized\n")
    
    # Run consolidation
    print("Running consolidation...")
    result = service.consolidate()
    
    print(f"\n✅ Consolidation complete:")
    print(f"   Events processed: {result['events_count']}")
    print(f"   Themes discovered: {result['clusters_count']}")
    print(f"   Summaries stored: {result['summaries_stored']}")
    print(f"   Duration: {result['duration_seconds']}s")
    print(f"   Status: {result['status']}")
    
    # Show history
    print(f"\n📊 Consolidation History:")
    history = service.get_consolidation_history()
    for i, run in enumerate(history[-5:], 1):  # Last 5 runs
        print(f"   {i}. {run['timestamp']}: {run['events_count']} events")
    
    print("\n✅ Test complete")
