"""
Test Phase 8: Distributed Consciousness

Validates distributed cognitive network:
- Peer registration and management
- State synchronization
- Consensus protocols
- Peer selection and ranking
- Network statistics
- Fault tolerance
"""

from chat_os.cognitive.distributed_consciousness import (
    ConsensusMethod,
    ConsensusProposal,
    DistributedConsciousness,
    PeerInfo,
    PeerStatus,
    StateUpdate,
    SyncStrategy,
    get_distributed_consciousness,
)


def test_peer_info_creation():
    """PeerInfo creates with valid attributes."""
    peer = PeerInfo(
        address="192.168.1.10:8000",
        status=PeerStatus.ACTIVE,
        max_load=100,
        reliability_score=0.95,
    )

    assert peer.peer_id is not None
    assert peer.address == "192.168.1.10:8000"
    assert peer.status == PeerStatus.ACTIVE
    assert peer.max_load == 100
    assert peer.reliability_score == 0.95


def test_peer_availability():
    """PeerInfo correctly reports availability."""
    peer = PeerInfo(
        status=PeerStatus.ACTIVE,
        max_load=100,
        current_load=50,
        reliability_score=0.8,
    )

    assert peer.is_available()

    # Over capacity
    peer.current_load = 100
    assert not peer.is_available()

    # Low reliability
    peer.current_load = 50
    peer.reliability_score = 0.2
    assert not peer.is_available()

    # Inactive
    peer.reliability_score = 0.8
    peer.status = PeerStatus.DISCONNECTED
    assert not peer.is_available()


def test_peer_reliability_update():
    """PeerInfo updates reliability based on outcomes."""
    peer = PeerInfo(reliability_score=0.5)

    # Success increases reliability
    initial = peer.reliability_score
    peer.update_reliability(True)
    assert peer.reliability_score > initial
    assert peer.successful_requests == 1

    # Failure decreases reliability
    initial = peer.reliability_score
    peer.update_reliability(False)
    assert peer.reliability_score < initial
    assert peer.failed_requests == 1


def test_state_update_creation():
    """StateUpdate creates with valid attributes."""
    update = StateUpdate(
        source_peer="peer-001",
        update_type="memory",
        operation="create",
        target_id="mem-001",
        data={"content": "test"},
        version=1,
    )

    assert update.update_id is not None
    assert update.source_peer == "peer-001"
    assert update.update_type == "memory"
    assert update.operation == "create"
    assert update.version == 1


def test_consensus_proposal_creation():
    """ConsensusProposal creates with valid attributes."""
    proposal = ConsensusProposal(
        proposer_peer="peer-001",
        proposal_type="action",
        description="Deploy new feature",
        data={"feature": "v2"},
    )

    assert proposal.proposal_id is not None
    assert proposal.proposer_peer == "peer-001"
    assert proposal.proposal_type == "action"
    assert not proposal.decided
    assert not proposal.approved


def test_distributed_consciousness_init():
    """DistributedConsciousness initializes correctly."""
    dc = DistributedConsciousness(
        instance_id="test-001", sync_strategy=SyncStrategy.IMMEDIATE
    )

    assert dc.instance_id == "test-001"
    assert dc.sync_strategy == SyncStrategy.IMMEDIATE
    assert len(dc.peers) == 0
    assert dc.local_peer.peer_id == "test-001"


def test_register_peer():
    """DistributedConsciousness registers peers."""
    dc = DistributedConsciousness()

    peer = PeerInfo(peer_id="peer-001", address="192.168.1.10:8000")
    dc.register_peer(peer)

    assert len(dc.peers) == 1
    assert "peer-001" in dc.peers
    assert dc.get_peer("peer-001") == peer


def test_unregister_peer():
    """DistributedConsciousness unregisters peers."""
    dc = DistributedConsciousness()

    peer = PeerInfo(peer_id="peer-001")
    dc.register_peer(peer)

    assert len(dc.peers) == 1

    dc.unregister_peer("peer-001")
    assert len(dc.peers) == 0


def test_get_active_peers():
    """DistributedConsciousness filters active peers."""
    dc = DistributedConsciousness()

    peer1 = PeerInfo(peer_id="peer-001", status=PeerStatus.ACTIVE)
    peer2 = PeerInfo(peer_id="peer-002", status=PeerStatus.DISCONNECTED)
    peer3 = PeerInfo(peer_id="peer-003", status=PeerStatus.ACTIVE)

    dc.register_peer(peer1)
    dc.register_peer(peer2)
    dc.register_peer(peer3)

    active = dc.get_active_peers()
    assert len(active) == 2
    assert peer1 in active
    assert peer3 in active


def test_get_available_peers():
    """DistributedConsciousness filters available peers."""
    dc = DistributedConsciousness()

    peer1 = PeerInfo(
        peer_id="peer-001",
        status=PeerStatus.ACTIVE,
        max_load=100,
        current_load=50,
        reliability_score=0.8,
    )
    peer2 = PeerInfo(
        peer_id="peer-002",
        status=PeerStatus.ACTIVE,
        max_load=100,
        current_load=100,  # At capacity
    )

    dc.register_peer(peer1)
    dc.register_peer(peer2)

    available = dc.get_available_peers()
    assert len(available) == 1
    assert peer1 in available


def test_select_peer_for_task():
    """DistributedConsciousness selects best peer for task."""
    dc = DistributedConsciousness()

    peer1 = PeerInfo(
        peer_id="peer-001",
        status=PeerStatus.ACTIVE,
        max_load=100,
        current_load=50,
        reliability_score=0.7,
    )
    peer2 = PeerInfo(
        peer_id="peer-002",
        status=PeerStatus.ACTIVE,
        max_load=100,
        current_load=20,
        reliability_score=0.9,
    )

    dc.register_peer(peer1)
    dc.register_peer(peer2)

    # peer2 should be selected (higher reliability, lower load)
    selected = dc.select_peer_for_task()
    assert selected == peer2


def test_create_state_update():
    """DistributedConsciousness creates state updates."""
    dc = DistributedConsciousness(instance_id="test-001")

    update = dc.create_state_update(
        update_type="memory",
        operation="create",
        target_id="mem-001",
        data={"content": "test"},
    )

    assert update.source_peer == "test-001"
    assert update.update_type == "memory"
    assert update.version == 1
    assert len(dc.pending_updates) == 1


def test_apply_state_update():
    """DistributedConsciousness applies state updates."""
    dc = DistributedConsciousness()

    update = StateUpdate(
        source_peer="peer-001",
        update_type="memory",
        operation="create",
        target_id="mem-001",
        data={"content": "test"},
        version=1,
    )

    success = dc.apply_state_update(update)
    assert success
    assert "mem-001" in dc.applied_updates
    assert len(dc.update_log) == 1


def test_apply_state_update_conflict():
    """DistributedConsciousness detects update conflicts."""
    dc = DistributedConsciousness()

    # Apply first update
    update1 = StateUpdate(
        target_id="mem-001",
        version=2,
        data={"content": "version 2"},
    )
    dc.apply_state_update(update1)

    # Try to apply older version (should conflict)
    update2 = StateUpdate(
        target_id="mem-001",
        version=1,
        data={"content": "version 1"},
    )
    success = dc.apply_state_update(update2)
    assert not success
    assert update2.conflict


def test_sync_with_peer():
    """DistributedConsciousness syncs with peers."""
    dc = DistributedConsciousness()

    peer = PeerInfo(peer_id="peer-001", status=PeerStatus.ACTIVE)
    dc.register_peer(peer)

    # Create update
    dc.create_state_update("memory", "create", "mem-001", {"content": "test"})

    # Sync
    success = dc.sync_with_peer("peer-001")
    assert success
    assert dc.total_syncs == 1
    assert dc.successful_syncs == 1
    assert len(dc.pending_updates) == 0


def test_sync_with_unreachable_peer():
    """DistributedConsciousness handles unreachable peers."""
    dc = DistributedConsciousness()

    peer = PeerInfo(peer_id="peer-001", status=PeerStatus.UNREACHABLE)
    dc.register_peer(peer)

    success = dc.sync_with_peer("peer-001")
    assert not success
    assert dc.failed_syncs == 1


def test_sync_all_peers():
    """DistributedConsciousness syncs with all peers."""
    dc = DistributedConsciousness()

    peer1 = PeerInfo(peer_id="peer-001", status=PeerStatus.ACTIVE)
    peer2 = PeerInfo(peer_id="peer-002", status=PeerStatus.ACTIVE)

    dc.register_peer(peer1)
    dc.register_peer(peer2)

    results = dc.sync_all_peers()
    assert len(results) == 2
    assert results["peer-001"] is True
    assert results["peer-002"] is True


def test_propose_consensus():
    """DistributedConsciousness creates consensus proposals."""
    dc = DistributedConsciousness(instance_id="test-001")

    proposal = dc.propose_consensus(
        proposal_type="action",
        description="Deploy feature",
        data={"feature": "v2"},
    )

    assert proposal.proposer_peer == "test-001"
    assert proposal.proposal_id in dc.active_proposals
    assert dc.total_consensus == 1


def test_vote_on_proposal():
    """DistributedConsciousness records votes."""
    dc = DistributedConsciousness()

    proposal = dc.propose_consensus("action", "Test", {})

    # Vote for
    success = dc.vote_on_proposal(proposal.proposal_id, "for", "peer-001")
    assert success
    assert "peer-001" in proposal.votes_for

    # Vote against
    success = dc.vote_on_proposal(proposal.proposal_id, "against", "peer-002")
    assert success
    assert "peer-002" in proposal.votes_against

    # Abstain
    success = dc.vote_on_proposal(proposal.proposal_id, "abstain", "peer-003")
    assert success
    assert "peer-003" in proposal.votes_abstain


def test_vote_change():
    """DistributedConsciousness allows vote changes."""
    dc = DistributedConsciousness()

    proposal = dc.propose_consensus("action", "Test", {})

    # Initial vote
    dc.vote_on_proposal(proposal.proposal_id, "for", "peer-001")
    assert "peer-001" in proposal.votes_for

    # Change vote
    dc.vote_on_proposal(proposal.proposal_id, "against", "peer-001")
    assert "peer-001" not in proposal.votes_for
    assert "peer-001" in proposal.votes_against


def test_consensus_majority():
    """DistributedConsciousness checks majority consensus."""
    dc = DistributedConsciousness()

    # Register 2 peers (+ self = 3 total)
    dc.register_peer(PeerInfo(peer_id="peer-001"))
    dc.register_peer(PeerInfo(peer_id="peer-002"))

    proposal = dc.propose_consensus("action", "Test", {})

    # 2 votes for, 1 against (majority for)
    dc.vote_on_proposal(proposal.proposal_id, "for", dc.instance_id)
    dc.vote_on_proposal(proposal.proposal_id, "for", "peer-001")
    dc.vote_on_proposal(proposal.proposal_id, "against", "peer-002")

    decided, approved = dc.check_consensus(proposal.proposal_id, ConsensusMethod.MAJORITY)
    assert decided
    assert approved


def test_consensus_unanimous():
    """DistributedConsciousness checks unanimous consensus."""
    dc = DistributedConsciousness()

    dc.register_peer(PeerInfo(peer_id="peer-001"))
    dc.register_peer(PeerInfo(peer_id="peer-002"))

    proposal = dc.propose_consensus("action", "Test", {})

    # All vote for
    dc.vote_on_proposal(proposal.proposal_id, "for", dc.instance_id)
    dc.vote_on_proposal(proposal.proposal_id, "for", "peer-001")
    dc.vote_on_proposal(proposal.proposal_id, "for", "peer-002")

    decided, approved = dc.check_consensus(proposal.proposal_id, ConsensusMethod.UNANIMOUS)
    assert decided
    assert approved


def test_consensus_not_reached():
    """DistributedConsciousness detects when consensus not reached."""
    dc = DistributedConsciousness()

    dc.register_peer(PeerInfo(peer_id="peer-001"))
    dc.register_peer(PeerInfo(peer_id="peer-002"))

    proposal = dc.propose_consensus("action", "Test", {})

    # Only 1 vote (not enough for majority)
    dc.vote_on_proposal(proposal.proposal_id, "for", dc.instance_id)

    decided, approved = dc.check_consensus(proposal.proposal_id, ConsensusMethod.MAJORITY)
    assert not decided


def test_consensus_weighted():
    """DistributedConsciousness uses weighted consensus."""
    dc = DistributedConsciousness()

    # Peer with high reliability
    peer1 = PeerInfo(peer_id="peer-001", reliability_score=0.9)
    # Peer with low reliability
    peer2 = PeerInfo(peer_id="peer-002", reliability_score=0.1)

    dc.register_peer(peer1)
    dc.register_peer(peer2)

    proposal = dc.propose_consensus("action", "Test", {})

    # High-reliability peer votes for, low-reliability votes against
    dc.vote_on_proposal(proposal.proposal_id, "for", "peer-001")
    dc.vote_on_proposal(proposal.proposal_id, "against", "peer-002")
    dc.vote_on_proposal(proposal.proposal_id, "for", dc.instance_id)

    decided, approved = dc.check_consensus(proposal.proposal_id, ConsensusMethod.WEIGHTED)
    assert decided
    assert approved  # Weighted for > weighted against


def test_consensus_leader():
    """DistributedConsciousness uses leader-based consensus."""
    dc = DistributedConsciousness(instance_id="leader-001")

    proposal = dc.propose_consensus("action", "Test", {})

    # Leader votes for
    dc.vote_on_proposal(proposal.proposal_id, "for", "leader-001")

    decided, approved = dc.check_consensus(proposal.proposal_id, ConsensusMethod.LEADER)
    assert decided
    assert approved


def test_get_network_stats():
    """DistributedConsciousness provides network statistics."""
    dc = DistributedConsciousness()

    dc.register_peer(PeerInfo(peer_id="peer-001", status=PeerStatus.ACTIVE))
    dc.register_peer(PeerInfo(peer_id="peer-002", status=PeerStatus.ACTIVE))

    stats = dc.get_network_stats()

    assert "instance_id" in stats
    assert stats["total_peers"] == 2
    assert stats["active_peers"] == 2
    assert "avg_reliability" in stats


def test_get_peer_rankings():
    """DistributedConsciousness ranks peers."""
    dc = DistributedConsciousness()

    peer1 = PeerInfo(
        peer_id="peer-001",
        status=PeerStatus.ACTIVE,
        max_load=100,
        current_load=50,
        reliability_score=0.9,
    )
    peer2 = PeerInfo(
        peer_id="peer-002",
        status=PeerStatus.ACTIVE,
        max_load=100,
        current_load=80,
        reliability_score=0.7,
    )

    dc.register_peer(peer1)
    dc.register_peer(peer2)

    rankings = dc.get_peer_rankings()

    assert len(rankings) == 2
    # peer1 should rank higher (better reliability, lower load)
    assert rankings[0][0] == "peer-001"
    assert rankings[0][1] > rankings[1][1]


def test_peer_status_enum():
    """PeerStatus enum has all expected values."""
    expected = [
        "CONNECTING",
        "ACTIVE",
        "IDLE",
        "BUSY",
        "UNREACHABLE",
        "DISCONNECTED",
    ]
    for status_name in expected:
        assert hasattr(PeerStatus, status_name)


def test_sync_strategy_enum():
    """SyncStrategy enum has all expected values."""
    expected = ["IMMEDIATE", "PERIODIC", "ON_DEMAND", "EVENTUAL"]
    for strategy_name in expected:
        assert hasattr(SyncStrategy, strategy_name)


def test_consensus_method_enum():
    """ConsensusMethod enum has all expected values."""
    expected = ["MAJORITY", "UNANIMOUS", "WEIGHTED", "LEADER"]
    for method_name in expected:
        assert hasattr(ConsensusMethod, method_name)


def test_global_singleton():
    """get_distributed_consciousness returns singleton."""
    dc1 = get_distributed_consciousness()
    dc2 = get_distributed_consciousness()

    assert dc1 is dc2
    assert isinstance(dc1, DistributedConsciousness)


def test_version_counter():
    """DistributedConsciousness increments version counter."""
    dc = DistributedConsciousness()

    update1 = dc.create_state_update("memory", "create", "mem-001", {})
    update2 = dc.create_state_update("memory", "create", "mem-002", {})

    assert update1.version == 1
    assert update2.version == 2
    assert dc.version_counter == 2


def test_update_log_trimming():
    """DistributedConsciousness trims update log."""
    dc = DistributedConsciousness()

    # Apply many updates
    for i in range(1100):
        update = StateUpdate(target_id=f"obj-{i}", version=i)
        dc.apply_state_update(update)

    # Log should be trimmed to 1000
    assert len(dc.update_log) == 1000


def test_consensus_history():
    """DistributedConsciousness tracks consensus history."""
    dc = DistributedConsciousness()

    dc.register_peer(PeerInfo(peer_id="peer-001"))

    proposal = dc.propose_consensus("action", "Test", {})

    # Vote and decide
    dc.vote_on_proposal(proposal.proposal_id, "for", dc.instance_id)
    dc.vote_on_proposal(proposal.proposal_id, "for", "peer-001")

    dc.check_consensus(proposal.proposal_id, ConsensusMethod.MAJORITY)

    # Should move to history
    assert len(dc.consensus_history) == 1
    assert proposal.proposal_id not in dc.active_proposals


def test_no_peers_selection():
    """DistributedConsciousness handles no available peers."""
    dc = DistributedConsciousness()

    # No peers registered
    selected = dc.select_peer_for_task()
    assert selected is None


# Phase 8 Complete: 30 tests validating distributed consciousness
