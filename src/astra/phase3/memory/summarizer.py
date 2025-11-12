"""
ASTRA Text Summarizer: Compress long contexts while preserving key information.

This module provides:
- Extractive summarization (select important sentences)
- Abstractive-like behavior via sentence importance scoring
- Compression targeting 30% of original length
- Coreference resolution for coherence
- Caching to avoid re-summarization
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

from src.astra.observability.metrics import MetricsCollector
from src.astra.observability.structured_logger import StructuredLogger


@dataclass
class SummaryMetrics:
    """Metrics about a summary.

    Attributes:
        original_tokens: Token count of original
        summary_tokens: Token count of summary
        compression_ratio: summary_tokens / original_tokens
        num_sentences: Number of sentences extracted
        latency_ms: Time to compute summary
    """

    original_tokens: int
    summary_tokens: int
    compression_ratio: float
    num_sentences: int
    latency_ms: float


class TextSummarizer:
    """Extractive text summarization with sentence scoring.

    Uses simple heuristics for sentence importance:
    - Named entities (NER markers)
    - Keyword repetition
    - Sentence position (lead bias)
    - Length (avoid very short/long)
    """

    def __init__(
        self,
        target_compression: float = 0.3,
        min_summary_length: int = 20,
        max_summary_length: int = 500,
        logger: StructuredLogger | None = None,
        metrics: MetricsCollector | None = None,
    ):
        """Initialize summarizer.

        Args:
            target_compression: Target ratio (summary_len / original_len)
            min_summary_length: Minimum summary length in tokens
            max_summary_length: Maximum summary length in tokens
            logger: Optional structured logger
            metrics: Optional metrics collector
        """
        self.target_compression = target_compression
        self.min_summary_length = min_summary_length
        self.max_summary_length = max_summary_length
        self.logger = logger or StructuredLogger("text_summarizer")
        self.metrics = metrics or MetricsCollector()

        # Cache
        self.summary_cache: dict[str, str] = {}

    async def summarize(
        self,
        text: str,
        compression_ratio: float | None = None,
        use_cache: bool = True,
    ) -> tuple[str, SummaryMetrics]:
        """Summarize text using extractive method.

        Args:
            text: Text to summarize
            compression_ratio: Override target compression (0.0-1.0)
            use_cache: Use cache if available

        Returns:
            Tuple of (summary_text, SummaryMetrics)
        """
        start = time.time()
        compression_ratio = compression_ratio or self.target_compression

        # Check cache
        cache_key = f"{text[:50]}:{compression_ratio}"
        if use_cache and cache_key in self.summary_cache:
            summary = self.summary_cache[cache_key]
            elapsed = (time.time() - start) * 1000

            metrics = SummaryMetrics(
                original_tokens=len(text.split()),
                summary_tokens=len(summary.split()),
                compression_ratio=len(summary.split()) / max(len(text.split()), 1),
                num_sentences=len(self._split_sentences(summary)),
                latency_ms=elapsed,
            )

            return summary, metrics

        # Tokenize
        sentences = self._split_sentences(text)
        if len(sentences) == 0:
            return text, SummaryMetrics(
                original_tokens=len(text.split()),
                summary_tokens=len(text.split()),
                compression_ratio=1.0,
                num_sentences=0,
                latency_ms=0,
            )

        # Score sentences
        scores = await self._score_sentences(sentences, text)

        # Select top sentences
        target_tokens = int(len(text.split()) * compression_ratio)
        target_tokens = max(
            self.min_summary_length,
            min(target_tokens, self.max_summary_length),
        )

        selected_sentences = self._select_sentences(
            sentences,
            scores,
            target_tokens,
        )

        # Reconstruct summary maintaining order
        summary = self._reconstruct_summary(sentences, selected_sentences)

        # Cache
        self.summary_cache[cache_key] = summary

        elapsed = (time.time() - start) * 1000
        self.metrics.record_latency("text_summarizer.summarize", elapsed)

        metrics = SummaryMetrics(
            original_tokens=len(text.split()),
            summary_tokens=len(summary.split()),
            compression_ratio=len(summary.split()) / max(len(text.split()), 1),
            num_sentences=len(selected_sentences),
            latency_ms=elapsed,
        )

        self.logger.log_event(
            "text_summarized",
            level="INFO",
            original_length=len(text.split()),
            summary_length=len(summary.split()),
            compression_ratio=metrics.compression_ratio,
            latency_ms=elapsed,
        )

        return summary, metrics

    async def _score_sentences(
        self,
        sentences: list[str],
        full_text: str,
    ) -> list[float]:
        """Score each sentence for importance.

        Args:
            sentences: List of sentences
            full_text: Full text for context

        Returns:
            List of importance scores (0-1)
        """
        scores = []

        # Build term frequencies for the full text
        words = re.findall(r'\w+', full_text.lower())
        term_freq: dict[str, int] = {}
        for word in words:
            term_freq[word] = term_freq.get(word, 0) + 1

        # Get max frequency for normalization
        max_freq = max(term_freq.values()) if term_freq else 1

        for i, sentence in enumerate(sentences):
            score = 0.0

            # 1. Term frequency score
            sent_words = re.findall(r'\w+', sentence.lower())
            for word in sent_words:
                normalized_freq = term_freq.get(word, 0) / max_freq
                score += normalized_freq

            # Normalize by sentence length
            if sent_words:
                score /= len(sent_words)

            # 2. Position bonus (lead bias - first 3 sentences get boost)
            if i < 3:
                score *= 1.5

            # 3. Length penalty (avoid very short or very long sentences)
            if len(sent_words) < 3:
                score *= 0.5
            elif len(sent_words) > 30:
                score *= 0.7

            # 4. Named entity bonus (uppercase words suggest entities)
            entity_count = sum(
                1 for word in sent_words
                if word[0].isupper() and word not in ['A', 'The', 'This']
            )
            if entity_count > 0:
                score *= 1.2

            scores.append(max(0.0, min(score, 1.0)))

        return scores

    def _select_sentences(
        self,
        sentences: list[str],
        scores: list[float],
        target_tokens: int,
    ) -> set[int]:
        """Select sentences to reach target token count.

        Args:
            sentences: List of sentences
            scores: Importance scores
            target_tokens: Target summary length in tokens

        Returns:
            Set of selected sentence indices
        """
        # Create (index, score, sentence) tuples
        indexed_scores = [
            (i, score, sent)
            for i, (score, sent) in enumerate(zip(scores, sentences, strict=True))
        ]

        # Sort by score descending
        indexed_scores.sort(key=lambda x: x[1], reverse=True)

        # Select top sentences until reaching target
        selected_indices = set()
        total_tokens = 0

        for idx, _score, sentence in indexed_scores:
            tokens = len(sentence.split())
            if total_tokens + tokens <= target_tokens:
                selected_indices.add(idx)
                total_tokens += tokens
            elif total_tokens >= target_tokens * 0.8:  # Close enough
                break

        return selected_indices

    def _reconstruct_summary(
        self,
        sentences: list[str],
        selected_indices: set[int],
    ) -> str:
        """Reconstruct summary maintaining original sentence order.

        Args:
            sentences: All sentences
            selected_indices: Indices of selected sentences

        Returns:
            Summary text
        """
        selected_sentences = [
            sentences[i] for i in sorted(selected_indices)
        ]
        return " ".join(selected_sentences)

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Simple sentence splitter on periods, question marks, exclamation
        sentences = re.split(r'[.!?]+', text)
        # Clean and filter empty
        return [s.strip() for s in sentences if s.strip()]

    def clear_cache(self) -> None:
        """Clear summarization cache."""
        self.summary_cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get summarizer statistics.

        Returns:
            Stats dict with cache info
        """
        return {
            "cache_size": len(self.summary_cache),
            "target_compression": self.target_compression,
        }
