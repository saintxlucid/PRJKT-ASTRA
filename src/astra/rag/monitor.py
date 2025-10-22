"""
Prometheus monitoring dashboard for RAG metrics.
"""
from typing import Dict, Any, Optional
import structlog
from prometheus_client import (
    start_http_server,
    Counter,
    Histogram,
    Gauge,
    CollectorRegistry,
    multiprocess
)
import time
import threading
from pathlib import Path

logger = structlog.get_logger(__name__)

class RAGMonitor:
    """Real-time monitoring dashboard for RAG metrics."""
    
    def __init__(
        self,
        port: int = 8000,
        metrics_dir: Optional[str] = None
    ):
        """Initialize monitoring.
        
        Args:
            port: Port for Prometheus metrics
            metrics_dir: Directory for persistent metrics
        """
        self.logger = logger.bind(component="rag_monitor")
        self.port = port
        
        # Setup registry
        if metrics_dir:
            Path(metrics_dir).mkdir(parents=True, exist_ok=True)
            self.registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(self.registry)
        else:
            self.registry = CollectorRegistry()
            
        # Query metrics
        self.query_counter = Counter(
            "rag_queries_total",
            "Total number of RAG queries",
            ["intent", "strategy"],
            registry=self.registry
        )
        
        self.query_latency = Histogram(
            "rag_query_latency_seconds",
            "RAG query latency in seconds",
            ["component"],
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            registry=self.registry
        )
        
        self.error_counter = Counter(
            "rag_errors_total", 
            "Total number of RAG errors",
            ["component", "type"],
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_hits = Counter(
            "rag_cache_hits_total",
            "Total number of cache hits",
            ["cache_type"],
            registry=self.registry
        )
        
        self.cache_misses = Counter(
            "rag_cache_misses_total",
            "Total number of cache misses",
            ["cache_type"],
            registry=self.registry
        )
        
        self.cache_size = Gauge(
            "rag_cache_size",
            "Current number of items in cache",
            ["cache_type"],
            registry=self.registry
        )
        
        # Retrieval metrics
        self.retrieval_scores = Histogram(
            "rag_retrieval_scores",
            "RAG retrieval relevance scores",
            ["metric"],
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
            registry=self.registry
        )
        
        self.docs_retrieved = Histogram(
            "rag_docs_retrieved",
            "Number of documents retrieved per query",
            buckets=(1, 2, 5, 10, 20, 50, 100),
            registry=self.registry
        )
        
        # System metrics
        self.gpu_memory = Gauge(
            "rag_gpu_memory_bytes",
            "GPU memory usage in bytes",
            ["device"],
            registry=self.registry
        )
        
        self.model_load_time = Histogram(
            "rag_model_load_seconds",
            "Time to load models in seconds",
            ["model"],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry
        )
        
        # Start metrics server
        self._start_server()
        
        # Background refresh thread
        self.running = True
        self.refresh_thread = threading.Thread(
            target=self._refresh_metrics,
            daemon=True
        )
        self.refresh_thread.start()
        
    def _start_server(self):
        """Start Prometheus metrics server."""
        try:
            start_http_server(
                self.port,
                registry=self.registry
            )
            self.logger.info(
                "metrics_server_started",
                port=self.port
            )
        except Exception as e:
            self.logger.error(
                "metrics_server_failed",
                error=str(e)
            )
            
    def _refresh_metrics(self):
        """Background metrics refresh."""
        while self.running:
            try:
                # Update GPU metrics
                try:
                    import torch
                    if torch.cuda.is_available():
                        for i in range(torch.cuda.device_count()):
                            mem_used = torch.cuda.memory_allocated(i)
                            self.gpu_memory.labels(
                                device=f"cuda:{i}"
                            ).set(mem_used)
                except:
                    pass
                    
                # Sleep
                time.sleep(15)
                
            except Exception as e:
                self.logger.error(
                    "metrics_refresh_failed",
                    error=str(e)
                )
                time.sleep(60)
                
    def track_query(
        self,
        query: str,
        intent: str,
        strategy: str,
        latency: float,
        num_results: int,
        scores: Optional[Dict[str, float]] = None,
        error: Optional[str] = None
    ):
        """
        Track query execution metrics.
        
        Args:
            query: Search query
            intent: Query intent 
            strategy: Retrieval strategy
            latency: Query latency in seconds
            num_results: Number of results returned
            scores: Optional relevance scores
            error: Optional error message
        """
        # Track query
        self.query_counter.labels(
            intent=intent,
            strategy=strategy
        ).inc()
        
        # Track latency
        self.query_latency.labels(
            component="total"
        ).observe(latency)
        
        # Track results
        self.docs_retrieved.observe(num_results)
        
        # Track scores
        if scores:
            for metric, score in scores.items():
                self.retrieval_scores.labels(
                    metric=metric
                ).observe(score)
                
        # Track errors
        if error:
            self.error_counter.labels(
                component="retrieval",
                type=error
            ).inc()
            
    def track_cache(
        self,
        cache_type: str,
        hit: bool,
        size: Optional[int] = None
    ):
        """
        Track cache metrics.
        
        Args:
            cache_type: Type of cache
            hit: Whether request was a hit
            size: Current cache size
        """
        if hit:
            self.cache_hits.labels(
                cache_type=cache_type
            ).inc()
        else:
            self.cache_misses.labels(
                cache_type=cache_type
            ).inc()
            
        if size is not None:
            self.cache_size.labels(
                cache_type=cache_type
            ).set(size)
            
    def track_model_load(
        self,
        model: str,
        load_time: float
    ):
        """
        Track model load times.
        
        Args:
            model: Model name/type
            load_time: Load time in seconds
        """
        self.model_load_time.labels(
            model=model
        ).observe(load_time)
        
    def track_error(
        self,
        component: str,
        error_type: str
    ):
        """
        Track system errors.
        
        Args:
            component: Component where error occurred
            error_type: Type of error
        """
        self.error_counter.labels(
            component=component,
            type=error_type
        ).inc()
        
    def shutdown(self):
        """Stop monitoring."""
        self.running = False
        if self.refresh_thread.is_alive():
            self.refresh_thread.join()