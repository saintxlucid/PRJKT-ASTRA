"""
ASTRA-OS Incident Bundler: Groups related threat indicators into incidents.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class IncidentStatus(Enum):
    """Incident lifecycle status."""
    ACTIVE = "active"
    ESCALATED = "escalated"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


@dataclass
class IncidentBundle:
    """Grouped incident with correlated indicators."""
    bundle_id: str
    timestamp: float
    status: IncidentStatus = IncidentStatus.ACTIVE
    threat_level: str = "MEDIUM"
    pattern_ids: Set[str] = field(default_factory=set)
    indicator_count: int = 0
    affected_processes: Set[int] = field(default_factory=set)
    affected_files: Set[str] = field(default_factory=set)
    affected_registry: Set[str] = field(default_factory=set)
    affected_ips: Set[str] = field(default_factory=set)
    description: str = ""
    confidence: float = 0.0
    related_bundles: Set[str] = field(default_factory=set)
    mitigation_applied: bool = False
    false_positive_confirmed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'bundle_id': self.bundle_id,
            'timestamp': self.timestamp,
            'status': self.status.value,
            'threat_level': self.threat_level,
            'pattern_ids': list(self.pattern_ids),
            'indicator_count': self.indicator_count,
            'affected_processes': list(self.affected_processes),
            'affected_files': list(self.affected_files),
            'affected_registry': list(self.affected_registry),
            'affected_ips': list(self.affected_ips),
            'description': self.description,
            'confidence': self.confidence,
            'related_bundles': list(self.related_bundles),
            'mitigation_applied': self.mitigation_applied,
            'false_positive_confirmed': self.false_positive_confirmed,
        }


# ============================================================================
# Correlation Engine
# ============================================================================

class CorrelationEngine:
    """Correlates threat indicators into bundles."""
    
    def __init__(self, time_window: int = 300):  # 5 minutes
        """Initialize correlation engine.
        
        Args:
            time_window: Time window for correlation (seconds)
        """
        self.time_window = time_window
        self.indicator_buffer: List[Any] = []
        self.recent_bundles: Dict[str, IncidentBundle] = {}
    
    def correlate(self, indicators: List[Any]) -> List[IncidentBundle]:
        """Correlate indicators into bundles.
        
        Args:
            indicators: List of threat indicators
            
        Returns:
            List of correlated incident bundles
        """
        if not indicators:
            return []
        
        bundles = []
        self.indicator_buffer.extend(indicators)
        
        # Clean old indicators
        current_time = time.time()
        self.indicator_buffer = [
            ind for ind in self.indicator_buffer
            if current_time - ind.get('timestamp', 0) < self.time_window
        ]
        
        # Group by pattern
        patterns = defaultdict(list)
        for indicator in self.indicator_buffer:
            pattern_id = indicator.get('pattern_id')
            patterns[pattern_id].append(indicator)
        
        # Create bundles for active patterns
        for pattern_id, group in patterns.items():
            if len(group) >= 2:  # At least 2 indicators
                bundle = self._create_bundle(pattern_id, group)
                bundles.append(bundle)
                self.recent_bundles[bundle.bundle_id] = bundle
        
        return bundles
    
    def _create_bundle(self, pattern_id: str, indicators: List[Any]) -> IncidentBundle:
        """Create incident bundle from correlated indicators."""
        bundle = IncidentBundle(
            bundle_id=f"BUNDLE_{int(time.time() * 1000)}_{hash(pattern_id) % 10000}",
            timestamp=time.time(),
            pattern_ids={pattern_id},
            indicator_count=len(indicators),
        )
        
        # Aggregate affected resources
        for indicator in indicators:
            evidence = indicator.get('evidence', {})
            
            if 'process_id' in indicator:
                bundle.affected_processes.add(indicator['process_id'])
            
            if 'file_path' in indicator:
                bundle.affected_files.add(indicator['file_path'])
            
            if 'registry_key' in indicator:
                bundle.affected_registry.add(indicator['registry_key'])
            
            if 'destination' in evidence:
                bundle.affected_ips.add(evidence['destination'])
        
        # Calculate aggregate confidence
        confidences = [ind.get('confidence', 0.5) for ind in indicators]
        bundle.confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        return bundle


# ============================================================================
# Incident Bundler
# ============================================================================

class IncidentBundler:
    """Groups related threat indicators into incidents."""
    
    def __init__(self, correlation_engine: Optional[CorrelationEngine] = None,
                 event_bus=None):
        """Initialize incident bundler.
        
        Args:
            correlation_engine: Engine for correlating indicators
            event_bus: Event bus for publishing bundles
        """
        self.correlation_engine = correlation_engine or CorrelationEngine()
        self.event_bus = event_bus
        self.incident_bundles: List[IncidentBundle] = []
        self.active_bundles: Dict[str, IncidentBundle] = {}
        self.bundle_timelines: Dict[str, List[IncidentBundle]] = defaultdict(list)
    
    async def bundle_indicators(self, indicators: List[Any]) -> List[IncidentBundle]:
        """Bundle threat indicators into incidents.
        
        Args:
            indicators: Raw threat indicators
            
        Returns:
            List of bundled incidents
        """
        if not indicators:
            return []
        
        # Correlate indicators
        bundles = self.correlation_engine.correlate(indicators)
        
        # Check for bundle merging
        bundles = self._merge_related_bundles(bundles)
        
        # Update tracking
        for bundle in bundles:
            self.incident_bundles.append(bundle)
            self.active_bundles[bundle.bundle_id] = bundle
            self.bundle_timelines[bundle.bundle_id].append(bundle)
        
        # Publish bundles to event bus
        if self.event_bus:
            for bundle in bundles:
                await self.event_bus.publish(
                    topic="sentinel/incident_bundle",
                    message=bundle.to_dict()
                )
        
        return bundles
    
    def _merge_related_bundles(self, bundles: List[IncidentBundle]) -> List[IncidentBundle]:
        """Merge related bundles that likely refer to same incident.
        
        Args:
            bundles: List of bundles to check for merging
            
        Returns:
            Deduplicated bundles
        """
        if not bundles:
            return []
        
        merged = []
        processed = set()
        
        for i, bundle1 in enumerate(bundles):
            if i in processed:
                continue
            
            # Check similarity with other bundles
            related = [bundle1]
            
            for j, bundle2 in enumerate(bundles[i+1:], i+1):
                if j in processed:
                    continue
                
                # Calculate similarity
                similarity = self._calculate_bundle_similarity(bundle1, bundle2)
                
                if similarity > 0.7:  # 70% similar = same incident
                    related.append(bundle2)
                    processed.add(j)
            
            # Merge related bundles
            if len(related) > 1:
                merged_bundle = self._merge_bundles(related)
                merged.append(merged_bundle)
                processed.add(i)
            else:
                merged.append(bundle1)
                processed.add(i)
        
        return merged
    
    def _calculate_bundle_similarity(self, bundle1: IncidentBundle, 
                                    bundle2: IncidentBundle) -> float:
        """Calculate similarity between two bundles (0.0-1.0).
        
        Args:
            bundle1: First bundle
            bundle2: Second bundle
            
        Returns:
            Similarity score
        """
        # Same pattern = high similarity
        if bundle1.pattern_ids & bundle2.pattern_ids:
            return 0.8
        
        # Same affected processes = high similarity
        if bundle1.affected_processes & bundle2.affected_processes:
            return 0.75
        
        # Same files or IPs = moderate similarity
        if bundle1.affected_files & bundle2.affected_files:
            return 0.6
        
        if bundle1.affected_ips & bundle2.affected_ips:
            return 0.6
        
        # Temporal proximity within 60 seconds
        time_diff = abs(bundle1.timestamp - bundle2.timestamp)
        if time_diff < 60:
            return 0.5
        
        return 0.0
    
    def _merge_bundles(self, bundles: List[IncidentBundle]) -> IncidentBundle:
        """Merge multiple bundles into single bundle.
        
        Args:
            bundles: Bundles to merge
            
        Returns:
            Merged bundle
        """
        merged = IncidentBundle(
            bundle_id=f"BUNDLE_{int(time.time() * 1000)}_MERGED",
            timestamp=min(b.timestamp for b in bundles),
            status=IncidentStatus.ACTIVE,
        )
        
        # Merge all fields
        for bundle in bundles:
            merged.pattern_ids.update(bundle.pattern_ids)
            merged.affected_processes.update(bundle.affected_processes)
            merged.affected_files.update(bundle.affected_files)
            merged.affected_registry.update(bundle.affected_registry)
            merged.affected_ips.update(bundle.affected_ips)
            merged.indicator_count += bundle.indicator_count
            merged.related_bundles.add(bundle.bundle_id)
        
        # Calculate aggregate confidence
        confidences = [b.confidence for b in bundles]
        merged.confidence = sum(confidences) / len(confidences)
        
        # Escalate threat level if any bundle is high/critical
        threat_levels = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        max_level = max(threat_levels.get(b.threat_level, 0) for b in bundles)
        level_map = {4: 'CRITICAL', 3: 'HIGH', 2: 'MEDIUM', 1: 'LOW'}
        merged.threat_level = level_map.get(max_level, 'MEDIUM')
        
        return merged
    
    def mark_resolved(self, bundle_id: str, false_positive: bool = False):
        """Mark incident bundle as resolved.
        
        Args:
            bundle_id: Bundle ID to mark
            false_positive: Whether this was a false positive
        """
        if bundle_id in self.active_bundles:
            bundle = self.active_bundles[bundle_id]
            bundle.status = IncidentStatus.RESOLVED
            
            if false_positive:
                bundle.false_positive_confirmed = True
                bundle.status = IncidentStatus.FALSE_POSITIVE
            
            logger.info(f"Marked bundle {bundle_id} as resolved")
    
    def escalate_bundle(self, bundle_id: str):
        """Escalate incident bundle threat level.
        
        Args:
            bundle_id: Bundle ID to escalate
        """
        if bundle_id in self.active_bundles:
            bundle = self.active_bundles[bundle_id]
            
            level_progression = {
                'LOW': 'MEDIUM',
                'MEDIUM': 'HIGH',
                'HIGH': 'CRITICAL',
                'CRITICAL': 'CRITICAL',
            }
            
            bundle.threat_level = level_progression.get(bundle.threat_level, bundle.threat_level)
            bundle.status = IncidentStatus.ESCALATED
            logger.warning(f"Escalated bundle {bundle_id} to {bundle.threat_level}")
    
    def mark_mitigated(self, bundle_id: str):
        """Mark incident bundle as mitigated.
        
        Args:
            bundle_id: Bundle ID to mark
        """
        if bundle_id in self.active_bundles:
            bundle = self.active_bundles[bundle_id]
            bundle.status = IncidentStatus.MITIGATED
            bundle.mitigation_applied = True
            logger.info(f"Marked bundle {bundle_id} as mitigated")
    
    def get_active_bundles(self) -> List[IncidentBundle]:
        """Get currently active incident bundles."""
        return [b for b in self.active_bundles.values() 
                if b.status == IncidentStatus.ACTIVE]
    
    def get_bundle_history(self, limit: int = 100) -> List[IncidentBundle]:
        """Get incident bundle history."""
        return self.incident_bundles[-limit:]
    
    def get_bundle_stats(self) -> Dict[str, Any]:
        """Get statistics on incident bundles."""
        return {
            'total_bundles': len(self.incident_bundles),
            'active_bundles': len(self.active_bundles),
            'resolved_bundles': sum(1 for b in self.incident_bundles if b.status == IncidentStatus.RESOLVED),
            'false_positives': sum(1 for b in self.incident_bundles if b.false_positive_confirmed),
            'escalations': sum(1 for b in self.incident_bundles if b.status == IncidentStatus.ESCALATED),
        }
    
    def get_bundle_timeline(self, bundle_id: str) -> List[IncidentBundle]:
        """Get timeline of bundle evolution."""
        return self.bundle_timelines.get(bundle_id, [])


if __name__ == "__main__":
    # Simple test
    bundler = IncidentBundler()
    
    # Create test indicators
    indicators = [
        {
            'pattern_id': 'P001',
            'timestamp': time.time(),
            'confidence': 0.8,
            'process_id': 1234,
            'evidence': {}
        },
        {
            'pattern_id': 'P001',
            'timestamp': time.time() + 5,
            'confidence': 0.85,
            'process_id': 1234,
            'evidence': {}
        }
    ]
    
    import asyncio
    bundles = asyncio.run(bundler.bundle_indicators(indicators))
    print(f"Created {len(bundles)} incident bundles")
    print(bundler.get_bundle_stats())
