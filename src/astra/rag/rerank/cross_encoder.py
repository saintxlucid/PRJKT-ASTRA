"""
Advanced cross-encoder reranker with layout-aware scoring, neural routing,
and adaptive reranking capabilities.

Features:
- Layout-aware scoring with bbox and section information
- Hierarchical context consideration with adaptive weighting
- Neural query intent routing and fusion
- Self-learning from feedback signals
- Consent-aware filtering
- MMR diversity with section awareness
"""
from typing import List, Dict, Any, Optional, Tuple, NamedTuple, Set, Union, TypedDict
import torch
import time
import re

class LayoutTelemetry(TypedDict):
    layout_scores: List[Dict[str, Any]]
    section_diversity: int
    heading_diversity: int
    answer_spans: int
    consent_filtered: int
    layout_enhanced: bool
import numpy as np
from dataclasses import dataclass, field
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import structlog
from pathlib import Path
import json
from datetime import datetime
from collections import defaultdict

logger = structlog.get_logger(__name__)

class BoundingBox(NamedTuple):
    """Page-relative bounding box."""
    x0: float  # Left coordinate
    y0: float  # Top coordinate
    x1: float  # Right coordinate
    y1: float  # Bottom coordinate
    page: int  # Page number

class TextChunk(NamedTuple):
    """Rich text chunk with layout information."""
    text: str
    bbox: Optional[BoundingBox] = None
    page: int = 0
    heading: Optional[str] = None
    section_id: Optional[str] = None
    policy: Dict[str, Any] = {}  # Consent/access policy
    metadata: Dict[str, Any] = {}

class QueryIntent(NamedTuple):
    """Query intent classification."""
    intent_type: str  # keyword, semantic, code, etc.
    confidence: float
    metadata: Dict[str, Any] = {}

@dataclass
class RerankerConfig:
    """Configuration for reranker with advanced features."""
    # Model settings
    model_name: str = "BAAI/bge-reranker-base"
    max_length: int = 512
    batch_size: int = 8
    use_fp16: bool = True
    min_answer_score: float = 0.3
    
    # Score weights & fusion
    fusion_weights: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "keyword": {"bm25": 0.7, "dense": 0.2, "rerank": 0.1},
        "semantic": {"bm25": 0.2, "dense": 0.5, "rerank": 0.3},
        "code": {"bm25": 0.4, "dense": 0.4, "rerank": 0.2}
    })
    
    # Layout & structure bonuses
    section_bonus: float = 0.1       # Bonus for distinct sections
    heading_bonus: float = 0.05      # Bonus for distinct headings
    length_bonus: float = 0.02       # Bonus per 100 tokens
    adjacency_bonus: float = 0.08    # Bonus for physically adjacent chunks
    table_context_bonus: float = 0.1 # Bonus for table-relevant content
    
    # Context bonuses
    history_bonus: float = 0.15      # Historical query relevance
    click_bonus: float = 0.12        # User click feedback bonus
    dwell_bonus: float = 0.08        # Reading time feedback bonus
    
    # Consent & filtering
    consent_required: bool = True     # Enable consent checking
    max_pii_density: float = 0.1     # Max allowed PII density
    scope_validation: bool = True     # Validate doc/chunk scope
    
    # Long document handling
    chunk_overlap: int = 50          # Token overlap between chunks
    max_context_chunks: int = 3      # Max chunks to combine
    min_chunk_score: float = 0.3     # Min score to include chunk
    
    # Query routing
    route_threshold: float = 0.7     # Min confidence for intent routing
    keyword_patterns: List[str] = field(default_factory=lambda: [
        r"\b(what|who|where|when|why|how)\b",
        r"\b(define|show|list|find|search)\b",
        r"\b(error|bug|issue|problem)\b"
    ])
    
    # Learning & adaptation
    learning_rate: float = 0.01      # Weight adjustment rate
    max_history_size: int = 1000     # Max feedback entries
    eval_frequency: int = 100        # Eval every N queries
    min_calibration_samples: int = 25 # Min samples for auto-tuning
    
    # Caching & performance
    cache_dir: str = "data/cache/reranker"
    cache_ttl: int = 3600           # Cache TTL in seconds
    max_cache_size: int = 10000     # Max cached items
    prefetch_size: int = 5          # Chunks to prefetch
    
    def __post_init__(self) -> None:
        """Validate configuration and compute derived values."""
        self._validate_weights()
        self._validate_params()
        self._init_telemetry()
        
    def _validate_weights(self) -> None:
        """Ensure weights are valid."""
        for intent, weights in self.fusion_weights.items():
            total = sum(weights.values())
            if not 0.99 <= total <= 1.01:
                raise ValueError(f"Weights for {intent} must sum to 1.0")
                
    def _init_telemetry(self) -> None:
        """Initialize telemetry trackers."""
        self.stats: Dict[str, Union[float, int]] = defaultdict(float)
        self.last_eval = datetime.now()
        self.samples_since_tune = 0
        
    def _validate_params(self) -> None:
        """Validate base configuration parameters."""
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.max_length <= 0:
            raise ValueError("max_length must be positive")
        if not (0 <= self.learning_rate <= 1):
            raise ValueError("learning_rate must be between 0 and 1")
        if not (0 <= self.length_bonus <= 1):
            raise ValueError("length_bonus must be between 0 and 1")
        if not (0 <= self.section_bonus <= 1):
            raise ValueError("section_bonus must be between 0 and 1")
        if not (0 <= self.heading_bonus <= 1):
            raise ValueError("heading_bonus must be between 0 and 1")
        if not (0 <= self.adjacency_bonus <= 1):
            raise ValueError("adjacency_bonus must be between 0 and 1")

class ChunkTelemetry(TypedDict):
    adjustments: List[Tuple[str, float]]
    filtered: bool
    chunk_id: int
    final_score: float
    section: Optional[str]
    heading: Optional[str]

class IntentStats(TypedDict):
    hits: int
    total: int

class CrossEncoder:
    """Lightweight cross-encoder reranker."""
    
    def __init__(self, config: Optional[RerankerConfig] = None):
        """Initialize reranker with config and optimizations."""
        self.score_cache: Dict[str, float] = {}
        self.config = config or RerankerConfig()
        self.logger = logger.bind(component="cross_encoder")
        
        # Initialize state
        self._initialize_state()
        
        # Create cache directory
        cache_dir = Path(self.config.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load model and tokenizer with optimizations
        try:
            # Initialize tokenizer with caching
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_name,
                cache_dir=str(cache_dir),
                use_fast=True  # Use fast tokenizer
            )
            
            # Load model with optimizations
            model_kwargs = {
                "cache_dir": str(cache_dir),
                "torch_dtype": torch.float16 if self.config.use_fp16 else torch.float32,
                "low_cpu_mem_usage": True
            }
            
            # Enable CUDA optimizations if available
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            if self.device == "cuda":
                model_kwargs.update({
                    "device_map": "auto",
                    "max_memory": {0: "4GB"}  # Adjust based on GPU memory
                })
            
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.config.model_name,
                **model_kwargs
            )
            
            # Apply optimization configs
            if self.device == "cuda":
                self.model.to(self.device)
                if self.config.use_fp16:
                    self.model.half()  # Convert to FP16
                    
            # Enable gradient checkpointing for memory efficiency
            if hasattr(self.model, "gradient_checkpointing_enable"):
                self.model.gradient_checkpointing_enable()
                
            # Initialize score cache
            self.score_cache = {}
            
            self.logger.info("reranker_initialized",
                           model=self.config.model_name,
                           device=self.device,
                           fp16=self.config.use_fp16,
                           batch_size=self.config.batch_size)
                           
        except Exception as e:
            self.logger.error("reranker_init_failed", 
                            error=str(e),
                            exc_info=True)
            raise
            
    def _initialize_state(self):
        """Initialize internal state and counters."""
        self.stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "avg_latency": 0.0,
            "rerank_calls": 0,
            "last_cleanup": time.time()
        }
        
        # Initialize feedback tracking
        self.feedback_buffer = []
        self.last_auto_tune = time.time()
        
        # Initialize component weights
        self.dynamic_weights = {
            "cross_encoder": 0.4,
            "layout": 0.3,
            "diversity": 0.3
        }
            
    def _prepare_pairs(
        self,
        query: str,
        texts: List[str]
    ) -> List[str]:
        """Prepare text pairs for cross-encoder."""
        return [
            f"{query} [SEP] {text}" 
            for text in texts
        ]
        
    def _batch_score(
        self,
        pairs: List[str],
        use_cache: bool = True
    ) -> np.ndarray:
        """
        Score a batch of text pairs with caching and error handling.
        
        Args:
            pairs: List of text pairs to score
            use_cache: Whether to use score caching
            
        Returns:
            Array of similarity scores
        """
        if not pairs:
            return np.array([])
            
        # Initialize cached scores
        cached_scores = []
            
        # Check cache first
        if use_cache:
            cached_scores = []
            uncached_pairs = []
            uncached_indices = []
            
            for i, pair in enumerate(pairs):
                if pair in self.score_cache:
                    cached_scores.append(self.score_cache[pair])
                else:
                    uncached_pairs.append(pair)
                    uncached_indices.append(i)
                    
            if not uncached_pairs:
                return np.array(cached_scores)
                
            pairs = uncached_pairs
        else:
            uncached_indices = list(range(len(pairs)))
            
        try:
            # Tokenize with error handling
            start_time = time.time()
            
            inputs = self.tokenizer(
                pairs,
                max_length=self.config.max_length,
                padding=True,
                truncation=True,
                return_tensors="pt",
                return_attention_mask=True  # Explicit attention mask
            )
            
            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Score in smaller batches if needed
            batch_size = self.config.batch_size
            all_scores = []
            
            for i in range(0, len(pairs), batch_size):
                batch_inputs = {
                    k: v[i:i + batch_size] 
                    for k, v in inputs.items()
                }
                
                # Forward pass with gradient disabled
                with torch.no_grad():
                    try:
                        outputs = self.model(**batch_inputs)
                        batch_scores = torch.softmax(outputs.logits, dim=1)
                        all_scores.append(batch_scores[:, 1].cpu())
                    except RuntimeError as e:
                        if "out of memory" in str(e):
                            # Clear cache and retry with smaller batch
                            torch.cuda.empty_cache()
                            batch_size = batch_size // 2
                            if batch_size < 1:
                                raise
                            continue
                        raise
                        
            scores = torch.cat(all_scores).numpy()
            
            # Update cache
            if use_cache:
                for pair, score in zip(pairs, scores):
                    self.score_cache[pair] = score
                    
                # Cleanup old cache entries if needed
                self._cleanup_cache()
                
            # Update stats
            duration = time.time() - start_time
            self.stats["avg_latency"] = (
                0.95 * self.stats["avg_latency"] + 
                0.05 * duration
            )
            self.stats["rerank_calls"] += 1
            
            # Reconstruct full score array
            if use_cache:
                full_scores = np.zeros(len(cached_scores) + len(scores))
                full_scores[uncached_indices] = scores
                
                j = 0
                for i in range(len(full_scores)):
                    if i not in uncached_indices:
                        full_scores[i] = cached_scores[j]
                        j += 1
                        
                return full_scores
                
            return scores
            
        except Exception as e:
            self.logger.error(
                "batch_scoring_failed",
                error=str(e),
                batch_size=len(pairs),
                exc_info=True
            )
            # Return zero scores on error
            return np.zeros(len(pairs))
            
    def _cleanup_cache(self) -> None:
        """Clean up old cache entries periodically."""
        current_time = time.time()
        if current_time - self.stats["last_cleanup"] > 3600:  # Cleanup every hour
            cache_size = len(self.score_cache)
            if cache_size > self.config.max_cache_size:
                # Remove oldest entries
                remove_count = int(0.2 * cache_size)  # Remove 20%
                keys_to_remove = list(self.score_cache.keys())[:remove_count]
                for key in keys_to_remove:
                    del self.score_cache[key]
                    
            self.stats["last_cleanup"] = current_time
            
    def _apply_layout_aware_scoring(
        self,
        query: str,
        chunks: List[TextChunk],
        scores: np.ndarray,
        intent: QueryIntent
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Apply comprehensive layout-aware scoring with telemetry.
        
        Features:
        - Layout proximity analysis
        - Section/heading diversity bonuses
        - Answer span detection
        - Historical interaction weighting
        - Policy compliance filtering
        - Telemetry collection
        """
        seen_sections = set()
        seen_headings = set()
        chunk_contexts = []
        
        # Initialize telemetry
        telemetry: LayoutTelemetry = {
            "layout_scores": [],
            "section_diversity": 0,
            "heading_diversity": 0,
            "answer_spans": 0,
            "consent_filtered": 0,
            "layout_enhanced": False
        }
        
        try:
            # First pass - collect layout context
            layout_context = defaultdict(list)
            for i, chunk in enumerate(chunks):
                if chunk.bbox:
                    layout_context[chunk.page].append((chunk, scores[i], i))
                    telemetry["layout_enhanced"] = True
                    
            # Second pass - compute layout-aware scores
            for i, chunk in enumerate(chunks):
                metadata = chunk.metadata
                text = chunk.text
                chunk_telemetry: ChunkTelemetry = {
                    "adjustments": [],
                    "filtered": False,
                    "chunk_id": 0,
                    "final_score": 0.0,
                    "section": None,
                    "heading": None
                }
                
                # 1. Structure Bonuses
                if chunk.section_id and chunk.section_id not in seen_sections:
                    section_bonus = self.config.section_bonus
                    scores[i] += section_bonus
                    seen_sections.add(chunk.section_id)
                    chunk_telemetry["adjustments"].append(
                        ("section_bonus", section_bonus)
                    )
                    telemetry["section_diversity"] += 1
                    
                if chunk.heading and chunk.heading not in seen_headings:
                    heading_bonus = self.config.heading_bonus
                    scores[i] += heading_bonus
                    seen_headings.add(chunk.heading)
                    chunk_telemetry["adjustments"].append(
                        ("heading_bonus", heading_bonus)
                    )
                    telemetry["heading_diversity"] += 1
                    
                # 2. Length Normalization
                token_count = len(self.tokenizer.encode(text))
                length_bonus = (token_count / 100.0) * self.config.length_bonus
                scores[i] += length_bonus
                chunk_telemetry["adjustments"].append(
                    ("length_bonus", length_bonus)
                )
                
                # 3. Layout Proximity Analysis
                if chunk.bbox:
                    page_chunks = layout_context[chunk.page]
                    layout_bonus = 0.0
                    
                    for other_chunk, other_score, other_idx in page_chunks:
                        if i != other_idx:
                            # Check visual relationships
                            v_overlap = self._vertical_overlap(
                                chunk.bbox, other_chunk.bbox
                            )
                            h_overlap = self._horizontal_overlap(
                                chunk.bbox, other_chunk.bbox
                            )
                            
                            # Detect reading order alignment
                            reading_order = self._check_reading_order(
                                chunk.bbox, other_chunk.bbox
                            )
                            
                            # Apply bonuses based on layout
                            if v_overlap > 0.5 or h_overlap > 0.5:
                                adjacency_bonus = (
                                    min(v_overlap, h_overlap) * 
                                    self.config.adjacency_bonus
                                )
                                layout_bonus += adjacency_bonus
                                
                            if reading_order > 0:
                                layout_bonus += (
                                    reading_order * 
                                    self.config.adjacency_bonus * 0.5
                                )
                                
                    scores[i] += layout_bonus
                    chunk_telemetry["adjustments"].append(
                        ("layout_bonus", layout_bonus)
                    )
                    
                # 4. Answer Span Analysis
                answer_score, spans = self._detect_answer_span(
                    query, text, int(64)
                )
                if answer_score > 0:
                    answer_bonus = answer_score
                    scores[i] *= (1.0 + answer_bonus)
                    chunk_contexts.append({
                        "chunk_idx": i,
                        "spans": spans,
                        "score": answer_score
                    })
                    chunk_telemetry["adjustments"].append(
                        ("answer_bonus", answer_bonus)
                    )
                    telemetry["answer_spans"] += 1
                    
                # 5. Historical Context Integration
                if "query_history" in metadata:
                    hist_bonus = self._compute_history_bonus(
                        query, text, metadata["query_history"]
                    )
                    scores[i] += hist_bonus
                    chunk_telemetry["adjustments"].append(
                        ("history_bonus", hist_bonus)
                    )
                    
                # 6. Policy Compliance Check
                if self.config.consent_required and chunk.policy:
                    if not self._validate_chunk_policy(chunk.policy):
                        scores[i] *= 0.1
                        telemetry["consent_filtered"] += 1
                        chunk_telemetry["filtered"] = True
                        
                # Record final chunk score
                chunk_telemetry = {
                    **chunk_telemetry,
                    "chunk_id": i,
                    "final_score": float(scores[i]),
                    "section": chunk.section_id,
                    "heading": chunk.heading
                }
                telemetry["layout_scores"].append(chunk_telemetry)
                
            # 7. Intent-Based Score Fusion
            weights = self.config.fusion_weights[intent.intent_type]
            if weights:
                for i, chunk in enumerate(chunks):
                    if all(k in chunk.metadata for k in ["bm25_score", "vector_score"]):
                        scores[i] = (
                            weights["bm25"] * float(chunk.metadata["bm25_score"]) +
                            weights["dense"] * float(chunk.metadata["vector_score"]) +
                            weights["rerank"] * float(scores[i])
                        )
                        
            # Update stats
            self._update_layout_stats(telemetry)
            
            return scores, chunk_contexts
            
        except Exception as e:
            self.logger.error(
                "layout_scoring_failed",
                error=str(e),
                exc_info=True
            )
            return scores, []
            
    def _check_reading_order(
        self,
        bbox1: BoundingBox,
        bbox2: BoundingBox
    ) -> float:
        """
        Check if chunks follow natural reading order.
        Returns score between 0-1 based on alignment.
        """
        if bbox1.page != bbox2.page:
            return 0.0
            
        # Left-to-right reading order
        if (bbox1.x1 < bbox2.x0 and 
            abs(bbox1.y0 - bbox2.y0) < 20):
            return 1.0
            
        # Top-to-bottom reading order  
        if (bbox1.y1 < bbox2.y0 and
            abs(bbox1.x0 - bbox2.x0) < 20):
            return 0.8
            
        return 0.0
        
    def _update_layout_stats(self, telemetry: LayoutTelemetry) -> None:
        """Update layout scoring statistics."""
        stats = self.stats
        stats["total_layouts_enhanced"] = (
            stats.get("total_layouts_enhanced", 0) +
            int(telemetry["layout_enhanced"])
        )
        stats["total_sections"] = (
            stats.get("total_sections", 0) + 
            telemetry["section_diversity"]
        )
        stats["total_headings"] = (
            stats.get("total_headings", 0) + 
            telemetry["heading_diversity"]
        )
        stats["total_answer_spans"] = (
            stats.get("total_answer_spans", 0) +
            telemetry["answer_spans"]
        )
        stats["total_filtered"] = (
            stats.get("total_filtered", 0) +
            telemetry["consent_filtered"]
        )
        
    def _vertical_overlap(self, bbox1: Optional[BoundingBox], bbox2: Optional[BoundingBox]) -> float:
        """Calculate vertical overlap ratio between two bboxes."""
        if not bbox1 or not bbox2 or bbox1.page != bbox2.page:
            return 0.0
        intersection = max(0, min(bbox1.y1, bbox2.y1) - max(bbox1.y0, bbox2.y0))
        union = max(bbox1.y1, bbox2.y1) - min(bbox1.y0, bbox2.y0)
        return intersection / union if union > 0 else 0.0
        
    def _horizontal_overlap(self, bbox1: Optional[BoundingBox], bbox2: Optional[BoundingBox]) -> float:
        """Calculate horizontal overlap ratio between two bboxes."""
        if not bbox1 or not bbox2 or bbox1.page != bbox2.page:
            return 0.0
        intersection = max(0, min(bbox1.x1, bbox2.x1) - max(bbox1.x0, bbox2.x0))
        union = max(bbox1.x1, bbox2.x1) - min(bbox1.x0, bbox2.x0)
        return intersection / union if union > 0 else 0.0
        
    def _compute_history_bonus(
        self,
        query: str,
        text: str,
        history: List[Dict[str, Any]]
    ) -> float:
        """Compute bonus based on historical interactions."""
        bonus = 0.0
        recent_history = history[-self.config.max_history_size:]
        
        for entry in recent_history:
            # Click-through bonus
            if entry.get("clicked", False):
                bonus += self.config.click_bonus
                
            # Dwell time bonus
            dwell_time = entry.get("dwell_time", 0)
            if dwell_time > 30:  # 30+ seconds considered good engagement
                bonus += self.config.dwell_bonus
                
            # Query similarity bonus
            if "query" in entry:
                hist_pairs = self._prepare_pairs(entry["query"], [text])
                hist_score = float(self._batch_score(hist_pairs)[0])
                bonus += hist_score * self.config.history_bonus
                
        return min(bonus, 0.5)  # Cap total bonus
        
    def _validate_chunk_policy(self, policy: Dict[str, Any]) -> bool:
        """Validate chunk against consent/access policy."""
        if not policy:
            return True
            
        # Check PII density
        if policy.get("pii_density", 0) > self.config.max_pii_density:
            return False
            
        # Check scope restrictions
        if "scope" in policy:
            # Add scope validation logic here
            return True
            
        return True
        
    def _classify_query_intent(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> QueryIntent:
        """
        Classify query intent for routing and weight selection.
        Uses pattern matching and learned embeddings.
        """
        # Fast pattern checks first
        query_lower = query.lower()
        for pattern_str in self.config.keyword_patterns:
            pattern = re.compile(pattern_str)
            if pattern.search(query_lower):
                return QueryIntent(
                    intent_type="keyword",
                    confidence=0.9,
                    metadata={"pattern_match": pattern_str}
                )
                
        # Code intent checks
        code_indicators = {
            "code", "function", "error", "bug", "api",
            "class", "method", "import", "runtime"
        }
        if any(ind in query_lower for ind in code_indicators):
            return QueryIntent(
                intent_type="code",
                confidence=0.85,
                metadata={"indicators": code_indicators & set(query_lower.split())}
            )
            
        # Use model for semantic classification
        inputs = self.tokenizer(
            [query],
            max_length=self.config.max_length,
            padding=True,
            truncation=True,
            return_tensors="pt"
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)
            
            # Map output logits to intents
            intent_scores = {
                "semantic": float(probs[0][0]),
                "keyword": float(probs[0][1]),
                "code": float(probs[0][2])
            }
            
            max_intent = max(intent_scores.items(), key=lambda x: x[1])
            
        return QueryIntent(
            intent_type=max_intent[0],
            confidence=max_intent[1],
            metadata={
                "scores": intent_scores,
                "query_length": len(query.split()),
                "context": context
            }
        )
        
    def _detect_answer_span(
        self,
        query: str,
        text: str,
        window_size: int = 64
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Enhanced answer span detection with context awareness.
        Returns (confidence, spans with metadata).
        """
        # Prepare sliding windows with overlap
        words = text.split()
        spans = []
        span_meta = []
        
        for i in range(0, len(words), window_size // 2):
            span = " ".join(words[i:i + window_size])
            span_words = span.split()
            
            # Extract potential structural markers
            has_bullet = any(w.startswith(("•", "-", "*")) for w in span_words)
            has_number = any(w[0].isdigit() and w[-1] == "." for w in span_words)
            
            spans.append(span)
            span_meta.append({
                "start_idx": i,
                "length": len(span_words),
                "has_bullet": has_bullet,
                "has_number": has_number
            })
            
        if not spans:
            return 0.0, []
            
        # Score spans
        pairs = self._prepare_pairs(query, spans)
        scores = self._batch_score(pairs)
        
        # Enhance promising spans
        enhanced_spans = []
        for i, (score, meta) in enumerate(zip(scores, span_meta)):
            if score > self.config.min_chunk_score:
                enhanced_spans.append({
                    **meta,
                    "text": spans[i],
                    "score": float(score),
                    "type": "answer_span"
                })
                
        # Sort by score
        enhanced_spans.sort(key=lambda x: x["score"], reverse=True)
        
        if enhanced_spans:
            return enhanced_spans[0]["score"], enhanced_spans
        return 0.0, []
    
    def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        return_scores: bool = False,
        batch_size: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Enhanced reranking with layout awareness and neural routing.
        
        Features:
        - Neural query intent classification
        - Layout-aware scoring
        - Context stitching
        - Answer span detection
        - Historical interaction learning
        - Consent-aware filtering
        - Auto-tuning score fusion
        
        Args:
            query: Search query
            results: Initial results to rerank
            return_scores: Include detailed scores
            batch_size: Override default batch size
            context: Additional context (history, user, etc.)
            
        Returns:
            Reranked and enhanced results
        """
        if not results:
            return results
            
        batch_size = batch_size or self.config.batch_size
        self.logger.info("reranking_started", query=query, num_results=len(results))
            
        try:
            # Stage 1: Query Intent Classification
            intent = self._classify_query_intent(query, context)
            self.logger.debug(
                "query_intent_classified",
                intent=intent.intent_type,
                confidence=intent.confidence
            )
            
            # Convert results to TextChunks
            chunks = [
                TextChunk(
                    text=r.get("text", ""),
                    bbox=BoundingBox(**r["bbox"]) if "bbox" in r else None,
                    page=r.get("page", 0),
                    heading=r.get("heading"),
                    section_id=r.get("section_id"),
                    policy=r.get("policy", {}),
                    metadata=r.get("metadata", {})
                )
                for r in results
            ]
            
            # Stage 2: Initial Scoring
            pairs = self._prepare_pairs(query, [c.text for c in chunks])
            all_scores = []
            
            # Batch scoring with progress tracking
            total_batches = (len(pairs) + batch_size - 1) // batch_size
            for i in range(0, len(pairs), batch_size):
                batch = pairs[i:i + batch_size]
                scores = self._batch_score(batch)
                all_scores.extend(scores)
                
                if total_batches > 10:
                    self.logger.debug(
                        "scoring_progress",
                        batch=f"{i // batch_size + 1}/{total_batches}"
                    )
                    
            base_scores = np.array(all_scores)
            
            # Stage 3: Layout-Aware Scoring & Context Collection
            scores, chunk_contexts = self._apply_layout_aware_scoring(
                query, chunks, base_scores, intent
            )
            
            # Stage 4: Context Stitching
            enhanced_chunks = self._stitch_contexts(
                chunks, chunk_contexts, scores
            )
            
            # Stage 5: Final Ranking & Formatting
            scored_results = list(zip(results, enhanced_chunks, scores))
            scored_results.sort(key=lambda x: x[2], reverse=True)
            
            # Update stats for auto-tuning
            self.config.samples_since_tune += 1
            if self.config.samples_since_tune >= self.config.eval_frequency:
                self._trigger_auto_tune()
            
            # Format output
            output = []
            for result, chunk, score in scored_results:
                if return_scores:
                    output.append({
                        **result,
                        "enhanced_text": chunk.text,
                        "rerank_score": float(score),
                        "score_components": {
                            "cross_encoder": float(score),
                            "bm25": chunk.metadata.get("bm25_score", 0.0),
                            "vector": chunk.metadata.get("vector_score", 0.0)
                        },
                        "context": {
                            "section": chunk.section_id,
                            "heading": chunk.heading,
                            "page": chunk.page,
                            "bbox": chunk.bbox._asdict() if chunk.bbox else None
                        },
                        "intent": {
                            "type": intent.intent_type,
                            "confidence": intent.confidence
                        }
                    })
                else:
                    output.append({
                        **result,
                        "enhanced_text": chunk.text
                    })
                    
            self.logger.info(
                "reranking_complete",
                query=query,
                intent=intent.intent_type,
                results=len(output)
            )
            return output
            
        except Exception as e:
            self.logger.error(
                "reranking_failed",
                query=query,
                error=str(e),
                exc_info=True
            )
            return results
            
    def _stitch_contexts(
        self,
        chunks: List[TextChunk],
        contexts: List[Dict[str, Any]],
        scores: np.ndarray
    ) -> List[TextChunk]:
        """
        Enhanced context stitching with layout awareness and telemetry.
        
        Features:
        - Layout-aware merging
        - Section continuity preservation
        - Citation management
        - Metadata fusion
        - Telemetry tracking
        """
        enhanced = []
        skip_indices = set()
        
        # Initialize telemetry
        stitch_telemetry = {
            "total_chunks": len(chunks),
            "merged_groups": 0,
            "total_merged": 0,
            "merge_patterns": defaultdict(int)
        }
        
        try:
            # Build section graph for continuity checking
            section_graph = self._build_section_graph(chunks)
            
            # Process chunks in reading order
            ordered_chunks = self._sort_reading_order(chunks)
            
            for i, (chunk_idx, chunk) in enumerate(ordered_chunks):
                if chunk_idx in skip_indices:
                    continue
                    
                score = scores[chunk_idx]
                if score < self.config.min_chunk_score:
                    enhanced.append(chunk)
                    continue
                    
                # Find merge candidates
                merge_group = self._find_merge_group(
                    chunk_idx,
                    chunks,
                    scores,
                    skip_indices,
                    section_graph
                )
                
                if len(merge_group) > 1:
                    # Merge chunks with enhanced logic
                    merged_chunk = self._merge_chunk_group(
                        merge_group,
                        chunks,
                        scores,
                        contexts
                    )
                    
                    # Update telemetry
                    stitch_telemetry["merged_groups"] += 1
                    stitch_telemetry["total_merged"] += len(merge_group)
                    merge_type = self._classify_merge_pattern(merge_group, chunks)
                    stitch_telemetry["merge_patterns"][merge_type] += 1
                    
                    # Mark chunks as processed
                    skip_indices.update(idx for idx, _, _ in merge_group)
                    
                    enhanced.append(merged_chunk)
                else:
                    enhanced.append(chunk)
                    
            # Log stitching telemetry
            self.logger.info(
                "context_stitching_complete",
                merged_groups=stitch_telemetry["merged_groups"],
                total_merged=stitch_telemetry["total_merged"],
                patterns=dict(stitch_telemetry["merge_patterns"])
            )
            
            return enhanced
            
        except Exception as e:
            self.logger.error(
                "context_stitching_failed",
                error=str(e),
                exc_info=True
            )
            return chunks
            
    def _build_section_graph(
        self,
        chunks: List[TextChunk]
    ) -> Dict[str, Set[str]]:
        """Build graph of section relationships."""
        graph = defaultdict(set)
        
        for chunk in chunks:
            if chunk.section_id:
                # Add hierarchical relationships
                parts = chunk.section_id.split(".")
                for i in range(len(parts)):
                    parent = ".".join(parts[:i])
                    child = ".".join(parts[:i+1])
                    if parent:
                        graph[parent].add(child)
                        
        return graph
        
    def _sort_reading_order(
        self,
        chunks: List[TextChunk]
    ) -> List[Tuple[int, TextChunk]]:
        """Sort chunks in natural reading order."""
        indexed_chunks = list(enumerate(chunks))
        
        def sort_key(item):
            idx, chunk = item
            if not chunk.bbox:
                return (float('inf'), float('inf'))
            return (chunk.page, -chunk.bbox.y0, chunk.bbox.x0)
            
        return sorted(indexed_chunks, key=sort_key)
        
    def _find_merge_group(
        self,
        start_idx: int,
        chunks: List[TextChunk],
        scores: np.ndarray,
        skip_indices: Set[int],
        section_graph: Dict[str, Set[str]]
    ) -> List[Tuple[int, TextChunk, float]]:
        """Find group of chunks to merge based on layout and content."""
        merge_group = [(start_idx, chunks[start_idx], scores[start_idx])]
        current_chunk = chunks[start_idx]
        
        # Look for merge candidates
        for i in range(start_idx + 1, len(chunks)):
            if i in skip_indices:
                continue
                
            next_chunk = chunks[i]
            next_score = scores[i]
            
            if next_score < self.config.min_chunk_score:
                continue
                
            # Check merge criteria
            if self._should_merge_chunks(current_chunk, next_chunk):
                # Check section continuity
                if (current_chunk.section_id and 
                    next_chunk.section_id and
                    not self._are_sections_related(
                        current_chunk.section_id,
                        next_chunk.section_id,
                        section_graph
                    )):
                    continue
                    
                merge_group.append((i, next_chunk, next_score))
                current_chunk = next_chunk
                
                if len(merge_group) >= self.config.max_context_chunks:
                    break
            else:
                break
                
        return merge_group
        
    def _merge_chunk_group(
        self,
        merge_group: List[Tuple[int, TextChunk, float]],
        chunks: List[TextChunk],
        scores: np.ndarray,
        contexts: List[Dict[str, Any]]
    ) -> TextChunk:
        """Merge a group of chunks with enhanced citation handling."""
        merged_text = []
        merged_meta = defaultdict(list)
        base_chunk = merge_group[0][1]
        
        for idx, chunk, score in merge_group:
            # Add section-aware citation
            citation = self._format_citation(chunk)
            
            # Check for relevant answer spans
            span_context = next(
                (ctx for ctx in contexts if ctx["chunk_idx"] == idx),
                None
            )
            
            if span_context:
                # Highlight answer spans
                text = self._highlight_spans(
                    chunk.text,
                    span_context["spans"]
                )
            else:
                text = chunk.text
                
            merged_text.append(f"{text} {citation}")
            
            # Collect metadata
            for k, v in chunk.metadata.items():
                merged_meta[k].append(v)
                
        # Process metadata
        final_meta = {}
        for k, values in merged_meta.items():
            if isinstance(values[0], (int, float)):
                final_meta[k] = np.mean(values)
            else:
                final_meta[k] = values[0]
                
        final_meta.update({
            "merged_chunks": len(merge_group),
            "merged_score": float(np.mean([s for _, _, s in merge_group])),
            "merge_type": self._classify_merge_pattern(merge_group, chunks)
        })
        
        return TextChunk(
            text=" ".join(merged_text),
            bbox=base_chunk.bbox,
            page=base_chunk.page,
            heading=base_chunk.heading,
            section_id=base_chunk.section_id,
            policy=base_chunk.policy,
            metadata=final_meta
        )
        
    def _format_citation(self, chunk: TextChunk) -> str:
        """Format citation with available metadata."""
        citation = [f"[p{chunk.page}"]
        
        if chunk.section_id:
            citation.append(f"§{chunk.section_id}")
            
        if chunk.heading:
            # Truncate long headings
            heading = chunk.heading
            if len(heading) > 30:
                heading = heading[:27] + "..."
            citation.append(f"h:{heading}")
            
        return " ".join(citation) + "]"
        
    def _highlight_spans(
        self,
        text: str,
        spans: List[Dict[str, Any]]
    ) -> str:
        """Add highlighting markers around answer spans."""
        if not spans:
            return text
            
        # Sort spans by score
        sorted_spans = sorted(
            spans,
            key=lambda x: x.get("score", 0),
            reverse=True
        )
        
        # Add highlighting tokens
        highlighted = text
        for span in sorted_spans[:3]:  # Limit to top 3 spans
            span_text = span["text"]
            if span_text in highlighted:
                highlighted = highlighted.replace(
                    span_text,
                    f"[START_HIGHLIGHT]{span_text}[END_HIGHLIGHT]"
                )
                
        return highlighted
        
    def _are_sections_related(
        self,
        section1: str,
        section2: str,
        section_graph: Dict[str, Set[str]]
    ) -> bool:
        """Check if sections are hierarchically related."""
        if section1 == section2:
            return True
            
        # Check if one is ancestor of other
        if section2 in section_graph.get(section1, set()):
            return True
            
        if section1 in section_graph.get(section2, set()):
            return True
            
        # Check for common ancestor
        parts1 = section1.split(".")
        parts2 = section2.split(".")
        
        return bool(
            len(parts1) > 1 and
            len(parts2) > 1 and
            parts1[0] == parts2[0]
        )
        
    def _classify_merge_pattern(
        self,
        merge_group: List[Tuple[int, TextChunk, float]],
        chunks: List[TextChunk]
    ) -> str:
        """Classify the type of merge pattern."""
        if len(merge_group) == 1:
            return "single"
            
        # Check if all chunks are from same section
        sections = {chunks[idx].section_id for idx, _, _ in merge_group}
        if len(sections) == 1:
            return "same_section"
            
        # Check if chunks are physically adjacent
        bboxes = [chunks[idx].bbox for idx, _, _ in merge_group if chunks[idx].bbox]
        if len(bboxes) > 1:
            v_aligned = all(
                self._vertical_overlap(b1, b2) > 0.5
                for b1, b2 in zip(bboxes, bboxes[1:])
            )
            h_aligned = all(
                self._horizontal_overlap(b1, b2) > 0.5
                for b1, b2 in zip(bboxes, bboxes[1:])
            )
            
            if v_aligned:
                return "vertical_merge"
            if h_aligned:
                return "horizontal_merge"
                
        return "mixed"
        
    def _should_merge_chunks(
        self,
        chunk1: TextChunk,
        chunk2: TextChunk
    ) -> bool:
        """Determine if two chunks should be merged based on layout and content."""
        # Must be on same page
        if chunk1.page != chunk2.page:
            return False
            
        # Check layout adjacency if bboxes exist
        if chunk1.bbox and chunk2.bbox:
            v_overlap = self._vertical_overlap(chunk1.bbox, chunk2.bbox)
            h_overlap = self._horizontal_overlap(chunk1.bbox, chunk2.bbox)
            
            # Merge if significant overlap
            if v_overlap > 0.7 or h_overlap > 0.7:
                return True
                
        # Check section/heading continuity
        if (
            chunk1.section_id == chunk2.section_id or
            chunk1.heading == chunk2.heading
        ):
            return True
            
        return False
        
    def _trigger_auto_tune(self):
        """Trigger weight auto-tuning based on collected feedback."""
        if len(self.config.stats) >= self.config.min_calibration_samples:
            self.logger.info("starting_auto_tune")
            
            # Compute success rates per intent
            intent_stats: Dict[str, IntentStats] = defaultdict(lambda: {"hits": 0, "total": 0})
            
            for key, value in self.config.stats.items():
                intent, metric = key.split(":")
                if metric == "hits":
                    intent_stats[intent]["hits"] += int(value)
                elif metric == "total":
                    intent_stats[intent]["total"] += int(value)
                    
            # Adjust weights based on performance
            for intent, stats in intent_stats.items():
                if stats["total"] > 0:
                    success_rate = stats["hits"] / stats["total"]
                    
                    # Adjust fusion weights
                    weights = self.config.fusion_weights[intent]
                    if success_rate < 0.7:  # Below target
                        # Increase weight of better performing retrievers
                        if stats.get("bm25_hits", 0) > stats.get("dense_hits", 0):
                            weights["bm25"] += self.config.learning_rate
                            weights["dense"] -= self.config.learning_rate
                        else:
                            weights["dense"] += self.config.learning_rate
                            weights["bm25"] -= self.config.learning_rate
                            
                    # Normalize weights
                    total = sum(weights.values())
                    for k in weights:
                        weights[k] /= total
                        
            # Reset stats
            self.config.stats.clear()
            self.config.samples_since_tune = 0
            self.logger.info("auto_tune_complete")
            
    def get_explanation(
        self,
        query: str,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get explanation for why a result was ranked highly.
        
        Args:
            query: Search query
            result: Result to explain
            
        Returns:
            Dict with explanation details
        """
        try:
            text = result.get("text", "")
            pair = self._prepare_pairs(query, [text])[0]
            
            # Get token contributions
            inputs = self.tokenizer(
                pair,
                max_length=self.config.max_length,
                padding=True,
                truncation=True,
                return_tensors="pt"
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Get attention weights
            with torch.no_grad():
                outputs = self.model(**inputs, output_attentions=True)
                
            # Get last layer attention
            attention = outputs.attentions[-1]  # [batch, heads, seq, seq]
            attention = attention.mean(dim=1)  # Average over heads
            
            # Get query token contributions
            query_tokens = self.tokenizer.tokenize(query)
            attention_scores = attention[0, :len(query_tokens), :].mean(dim=0)
            
            # Get top contributing spans
            spans = []
            tokens = self.tokenizer.convert_ids_to_tokens(
                inputs["input_ids"][0]
            )
            
            # Find spans with high attention
            i = 0
            while i < len(tokens):
                if attention_scores[i] > 0.1:  # Attention threshold
                    span_tokens = []
                    while (i < len(tokens) and 
                           attention_scores[i] > 0.05):  # Continue threshold
                        span_tokens.append(tokens[i])
                        i += 1
                    if span_tokens:
                        spans.append({
                            "text": self.tokenizer.convert_tokens_to_string(
                                span_tokens
                            ),
                            "score": float(attention_scores[i-1])
                        })
                i += 1
                
            return {
                "matched_spans": spans,
                "metadata": result.get("metadata", {}),
                "overall_score": float(outputs.logits[0, 1])
            }
            
        except Exception as e:
            self.logger.error("explanation_failed",
                            query=query,
                            error=str(e))
            return {}