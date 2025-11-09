"""
Phase 8: Distributed Consciousness

Enables multiple ASTRA instances to form a federated cognitive network:
- Peer discovery and connection management
- Shared cognitive state synchronization
- Distributed memory and knowledge graph
- Coordinated multi-agent execution
- Consensus-based decision making
- Fault tolerance and recovery
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PeerStatus(Enum):
    """Status of a peer instance."""

    CONNECTING = "connecting"
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    UNREACHABLE = "unreachable"
    DISCONNECTED = "disconnected"


class SyncStrategy(Enum):
    """Strategy for state synchronization."""

    IMMEDIATE = "immediate"  # Sync every change
    PERIODIC = "periodic"  # Sync at intervals
    ON_DEMAND = "on_demand"  # Sync only when requested
    EVENTUAL = "eventual"  # Eventually consistent


class ConsensusMethod(Enum):
    """Method for reaching consensus."""

    MAJORITY = "majority"  # Simple majority vote
    UNANIMOUS = "unanimous"  # All peers must agree
    WEIGHTED = "weighted"  # Weighted by peer reliability
    LEADER = "leader"  # Leader decides


@dataclass
class PeerInfo:
    """
    Information about a peer ASTRA instance.

    Represents a remote instance in the distributed network.
    """

    peer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    address: str = ""  # Network address (host:port or URI)
    status: PeerStatus = PeerStatus.CONNECTING

    # Capabilities
    capabilities: set[str] = field(default_factory=set)
    max_load: int = 100  # Max concurrent tasks
    current_load: int = 0

    # Reliability
    reliability_score: float = 1.0  # [0-1] based on uptime/success
    last_seen: float = field(default_factory=time.time)
    response_time: float = 0.0  # Average response time (seconds)

    # Statistics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    metadata: dict[str, Any] = field(default_factory=dict)

    def update_reliability(self, success: bool) -> None:
        """Update reliability score based on request outcome."""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
            # Increase reliability slightly
            self.reliability_score = min(
                1.0, self.reliability_score + 0.01 * (1.0 - self.reliability_score)
            )
        else:
            self.failed_requests += 1
            # Decrease reliability more aggressively
            self.reliability_score = max(0.0, self.reliability_score - 0.05)

    def is_available(self) -> bool:
        """Check if peer is available for work."""
        return (
            self.status == PeerStatus.ACTIVE
            and self.current_load < self.max_load
            and self.reliability_score > 0.3
        )


@dataclass
class StateUpdate:
    """
    A state synchronization update.

    Represents a change to shared cognitive state.
    """

    update_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_peer: str = ""  # Originating peer ID
    timestamp: float = field(default_factory=time.time)

    # Update content
    update_type: str = ""  # "memory", "graph", "learning", "config"
    operation: str = ""  # "create", "update", "delete"
    target_id: str = ""  # ID of affected object
    data: dict[str, Any] = field(default_factory=dict)

    # Versioning
    version: int = 1
    previous_version: int = 0

    # Conflict resolution
    conflict: bool = False
    conflict_resolution: str | None = None


@dataclass
class ConsensusProposal:
    """
    A proposal requiring consensus from peers.

    Used for coordinated decision-making.
    """

    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    proposer_peer: str = ""
    timestamp: float = field(default_factory=time.time)

    # Proposal details
    proposal_type: str = ""  # "action", "configuration", "policy"
    description: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    # Voting
    votes_for: set[str] = field(default_factory=set)  # Peer IDs
    votes_against: set[str] = field(default_factory=set)
    votes_abstain: set[str] = field(default_factory=set)

    # Status
    decided: bool = False
    approved: bool = False
    decision_time: float | None = None


class DistributedConsciousness:
    """
    Distributed cognitive network coordinator.

    Manages peer connections, state synchronization, and consensus.
    """

    def __init__(
        self,
        instance_id: str | None = None,
        sync_strategy: SyncStrategy = SyncStrategy.PERIODIC,
    ):
        """
        Initialize distributed consciousness coordinator.

        Args:
            instance_id: Unique ID for this instance
            sync_strategy: Strategy for state synchronization
        """
        self.instance_id = instance_id or str(uuid.uuid4())
        self.sync_strategy = sync_strategy

        # Peer management
        self.peers: dict[str, PeerInfo] = {}
        self.local_peer = PeerInfo(
            peer_id=self.instance_id,
            address="local",
            status=PeerStatus.ACTIVE,
        )

        # State synchronization
        self.pending_updates: list[StateUpdate] = []
        self.applied_updates: dict[str, StateUpdate] = {}  # update_id -> update
        self.update_log: list[StateUpdate] = []
        self.version_counter: int = 0

        # Consensus
        self.active_proposals: dict[str, ConsensusProposal] = {}
        self.consensus_history: list[ConsensusProposal] = []

        # Statistics
        self.total_syncs: int = 0
        self.successful_syncs: int = 0
        self.failed_syncs: int = 0
        self.total_consensus: int = 0

    def register_peer(self, peer: PeerInfo) -> None:
        """
        Register a new peer in the network.

        Args:
            peer: Peer information
        """
        self.peers[peer.peer_id] = peer

    def unregister_peer(self, peer_id: str) -> None:
        """
        Remove a peer from the network.

        Args:
            peer_id: ID of peer to remove
        """
        if peer_id in self.peers:
            self.peers[peer_id].status = PeerStatus.DISCONNECTED
            del self.peers[peer_id]

    def get_peer(self, peer_id: str) -> PeerInfo | None:
        """Get peer information by ID."""
        return self.peers.get(peer_id)

    def get_active_peers(self) -> list[PeerInfo]:
        """Get all active peers."""
        return [p for p in self.peers.values() if p.status == PeerStatus.ACTIVE]

    def get_available_peers(self) -> list[PeerInfo]:
        """Get peers available for work."""
        return [p for p in self.peers.values() if p.is_available()]

    def select_peer_for_task(self) -> PeerInfo | None:
        """
        Select best peer for task execution.

        Returns peer with highest reliability and lowest load.
        """
        available = self.get_available_peers()
        if not available:
            return None

        # Score = reliability / (1 + load_ratio)
        def score_peer(peer: PeerInfo) -> float:
            load_ratio = peer.current_load / peer.max_load
            return peer.reliability_score / (1 + load_ratio)

        return max(available, key=score_peer)

    def create_state_update(
        self, update_type: str, operation: str, target_id: str, data: dict[str, Any]
    ) -> StateUpdate:
        """
        Create a state synchronization update.

        Args:
            update_type: Type of update (memory, graph, learning, config)
            operation: Operation (create, update, delete)
            target_id: ID of affected object
            data: Update data

        Returns:
            Created state update
        """
        self.version_counter += 1

        update = StateUpdate(
            source_peer=self.instance_id,
            update_type=update_type,
            operation=operation,
            target_id=target_id,
            data=data,
            version=self.version_counter,
        )

        self.pending_updates.append(update)
        return update

    def apply_state_update(self, update: StateUpdate) -> bool:
        """
        Apply a state update to local state.

        Args:
            update: State update to apply

        Returns:
            True if applied successfully
        """
        # Check for conflicts
        if update.target_id in self.applied_updates:
            existing = self.applied_updates[update.target_id]
            if existing.version >= update.version:
                # Conflict: existing version is newer or same
                update.conflict = True
                return False

        # Apply update
        self.applied_updates[update.target_id] = update
        self.update_log.append(update)

        # Trim log if too large
        if len(self.update_log) > 1000:
            self.update_log = self.update_log[-1000:]

        return True

    def sync_with_peer(self, peer_id: str) -> bool:
        """
        Synchronize state with a specific peer.

        Args:
            peer_id: ID of peer to sync with

        Returns:
            True if sync successful
        """
        peer = self.get_peer(peer_id)
        if not peer or peer.status != PeerStatus.ACTIVE:
            self.failed_syncs += 1
            return False

        try:
            # Send pending updates to peer
            for update in self.pending_updates:
                # In real implementation, would send over network
                pass

            self.pending_updates.clear()
            self.total_syncs += 1
            self.successful_syncs += 1

            # Update peer stats
            peer.last_seen = time.time()
            peer.update_reliability(True)

            return True

        except Exception:
            self.failed_syncs += 1
            if peer:
                peer.update_reliability(False)
            return False

    def sync_all_peers(self) -> dict[str, bool]:
        """
        Synchronize with all active peers.

        Returns:
            Dict mapping peer_id to sync success
        """
        results = {}
        for peer_id in list(self.peers.keys()):
            results[peer_id] = self.sync_with_peer(peer_id)
        return results

    def propose_consensus(
        self, proposal_type: str, description: str, data: dict[str, Any]
    ) -> ConsensusProposal:
        """
        Propose an action requiring consensus.

        Args:
            proposal_type: Type of proposal
            description: Human-readable description
            data: Proposal data

        Returns:
            Created consensus proposal
        """
        proposal = ConsensusProposal(
            proposer_peer=self.instance_id,
            proposal_type=proposal_type,
            description=description,
            data=data,
        )

        self.active_proposals[proposal.proposal_id] = proposal
        self.total_consensus += 1

        return proposal

    def vote_on_proposal(
        self, proposal_id: str, vote: str, peer_id: str | None = None
    ) -> bool:
        """
        Vote on a consensus proposal.

        Args:
            proposal_id: ID of proposal
            vote: "for", "against", or "abstain"
            peer_id: ID of voting peer (defaults to self)

        Returns:
            True if vote recorded
        """
        proposal = self.active_proposals.get(proposal_id)
        if not proposal or proposal.decided:
            return False

        voter = peer_id or self.instance_id

        # Remove from other vote sets
        proposal.votes_for.discard(voter)
        proposal.votes_against.discard(voter)
        proposal.votes_abstain.discard(voter)

        # Add to appropriate set
        if vote == "for":
            proposal.votes_for.add(voter)
        elif vote == "against":
            proposal.votes_against.add(voter)
        elif vote == "abstain":
            proposal.votes_abstain.add(voter)
        else:
            return False

        return True

    def check_consensus(
        self, proposal_id: str, method: ConsensusMethod = ConsensusMethod.MAJORITY
    ) -> tuple[bool, bool]:
        """
        Check if consensus has been reached on a proposal.

        Args:
            proposal_id: ID of proposal
            method: Consensus method to use

        Returns:
            (decided, approved) tuple
        """
        proposal = self.active_proposals.get(proposal_id)
        if not proposal:
            return False, False

        if proposal.decided:
            return True, proposal.approved

        total_peers = len(self.peers) + 1  # Include self
        votes_for = len(proposal.votes_for)
        votes_against = len(proposal.votes_against)
        total_votes = votes_for + votes_against + len(proposal.votes_abstain)

        decided = False
        approved = False

        if method == ConsensusMethod.MAJORITY:
            # Simple majority of votes
            if total_votes >= total_peers // 2 + 1:
                decided = True
                approved = votes_for > votes_against

        elif method == ConsensusMethod.UNANIMOUS:
            # All peers must vote for
            if total_votes == total_peers:
                decided = True
                approved = votes_for == total_peers

        elif method == ConsensusMethod.WEIGHTED:
            # Weight by peer reliability
            weighted_for = sum(
                self.peers.get(p, self.local_peer).reliability_score
                for p in proposal.votes_for
            )
            weighted_against = sum(
                self.peers.get(p, self.local_peer).reliability_score
                for p in proposal.votes_against
            )

            if total_votes >= total_peers // 2 + 1:
                decided = True
                approved = weighted_for > weighted_against

        elif method == ConsensusMethod.LEADER:
            # Proposer decides (leader)
            if proposal.proposer_peer in proposal.votes_for:
                decided = True
                approved = True
            elif proposal.proposer_peer in proposal.votes_against:
                decided = True
                approved = False

        if decided:
            proposal.decided = True
            proposal.approved = approved
            proposal.decision_time = time.time()

            # Move to history
            self.consensus_history.append(proposal)
            if proposal_id in self.active_proposals:
                del self.active_proposals[proposal_id]

        return decided, approved

    def get_network_stats(self) -> dict[str, Any]:
        """Get network statistics."""
        active_count = len(self.get_active_peers())
        available_count = len(self.get_available_peers())

        avg_reliability = (
            sum(p.reliability_score for p in self.peers.values()) / len(self.peers)
            if self.peers
            else 0.0
        )

        return {
            "instance_id": self.instance_id,
            "total_peers": len(self.peers),
            "active_peers": active_count,
            "available_peers": available_count,
            "avg_reliability": avg_reliability,
            "total_syncs": self.total_syncs,
            "successful_syncs": self.successful_syncs,
            "failed_syncs": self.failed_syncs,
            "sync_success_rate": (
                self.successful_syncs / self.total_syncs if self.total_syncs > 0 else 0
            ),
            "pending_updates": len(self.pending_updates),
            "applied_updates": len(self.applied_updates),
            "active_proposals": len(self.active_proposals),
            "total_consensus": self.total_consensus,
        }

    def get_peer_rankings(self) -> list[tuple[str, float]]:
        """
        Get peers ranked by suitability for task execution.

        Returns:
            List of (peer_id, score) tuples, highest first
        """
        rankings = []
        for peer in self.peers.values():
            if peer.is_available():
                load_ratio = peer.current_load / peer.max_load
                score = peer.reliability_score / (1 + load_ratio)
                rankings.append((peer.peer_id, score))

        return sorted(rankings, key=lambda x: x[1], reverse=True)


# Global distributed consciousness singleton
_distributed_consciousness: DistributedConsciousness | None = None


def get_distributed_consciousness() -> DistributedConsciousness:
    """Get global distributed consciousness singleton."""
    global _distributed_consciousness
    if _distributed_consciousness is None:
        _distributed_consciousness = DistributedConsciousness()
    return _distributed_consciousness


# Example usage
if __name__ == "__main__":
    # Create distributed network
    dc = get_distributed_consciousness()

    # Register peers
    peer1 = PeerInfo(
        peer_id="peer-001",
        address="192.168.1.10:8000",
        status=PeerStatus.ACTIVE,
        capabilities={"symbolic", "statistical"},
        max_load=50,
    )
    peer2 = PeerInfo(
        peer_id="peer-002",
        address="192.168.1.11:8000",
        status=PeerStatus.ACTIVE,
        capabilities={"procedural", "statistical"},
        max_load=100,
    )

    dc.register_peer(peer1)
    dc.register_peer(peer2)

    print(f"Network has {len(dc.peers)} peers")

    # Create state update
    update = dc.create_state_update(
        update_type="memory",
        operation="create",
        target_id="mem-001",
        data={"content": "Test memory", "embedding": [0.1, 0.2, 0.3]},
    )
    print(f"\nCreated update: {update.update_id}")

    # Sync with peers
    results = dc.sync_all_peers()
    print(f"\nSync results: {results}")

    # Propose consensus
    proposal = dc.propose_consensus(
        proposal_type="action",
        description="Deploy new cognitive graph",
        data={"graph_id": "graph-v2", "priority": "high"},
    )
    print(f"\nProposal created: {proposal.proposal_id}")

    # Vote on proposal
    dc.vote_on_proposal(proposal.proposal_id, "for", dc.instance_id)
    dc.vote_on_proposal(proposal.proposal_id, "for", "peer-001")
    dc.vote_on_proposal(proposal.proposal_id, "against", "peer-002")

    # Check consensus
    decided, approved = dc.check_consensus(proposal.proposal_id, ConsensusMethod.MAJORITY)
    print(f"\nConsensus: decided={decided}, approved={approved}")

    # Get network stats
    stats = dc.get_network_stats()
    print("\nNetwork statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Get peer rankings
    rankings = dc.get_peer_rankings()
    print("\nPeer rankings:")
    for peer_id, score in rankings:
        print(f"  {peer_id}: {score:.3f}")
