# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: nonecheck=False
# cython: cdivision=True

"""
Distributed Consensus Kernel
==============================

High-performance primitives for multi-agent consensus protocols,
Byzantine fault tolerance, and leader election at C-speed.

Key algorithms:
- Paxos-like consensus
- RAFT leader election
- Byzantine agreement (simplified)
- Gossip protocols
- Quorum detection

Designed for ASTRA's multi-agent orchestration.
"""

import numpy as np
cimport numpy as cnp
cimport cython
from libc.math cimport exp, log, sqrt, fabs
from libc.stdlib cimport rand, RAND_MAX

cnp.import_array()


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int detect_quorum(
    int[:] agent_votes,
    int num_agents,
    float quorum_threshold
) nogil:
    """
    Detect if quorum is reached (majority agreement).
    
    Args:
        agent_votes: (N,) agent votes (0 or 1)
        num_agents: number of agents
        quorum_threshold: fraction needed [0, 1]
        
    Returns:
        1 if quorum reached, 0 otherwise
    """
    cdef Py_ssize_t i
    cdef int yes_votes = 0
    
    for i in range(num_agents):
        if agent_votes[i] == 1:
            yes_votes += 1
    
    if <float>yes_votes / <float>num_agents >= quorum_threshold:
        return 1
    return 0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int elect_leader_bully(
    int[:] agent_ids,
    int[:] agent_health,
    int num_agents
) nogil:
    """
    Elect leader using Bully algorithm (highest healthy ID wins).
    
    Args:
        agent_ids: (N,) unique agent IDs
        agent_health: (N,) 1 if healthy, 0 if failed
        num_agents: number of agents
        
    Returns:
        leader_id: elected leader's ID
    """
    cdef Py_ssize_t i
    cdef int max_id = -1
    
    for i in range(num_agents):
        if agent_health[i] == 1 and agent_ids[i] > max_id:
            max_id = agent_ids[i]
    
    return max_id


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_agent_trust_scores(
    float[:, :] interaction_history,
    int num_agents,
    float[:] trust_scores_out
) nogil:
    """
    Compute trust scores based on interaction history.
    
    Args:
        interaction_history: (N, N) pairwise interaction success rates
        num_agents: number of agents
        trust_scores_out: (N,) aggregated trust scores [0, 1]
    """
    cdef Py_ssize_t i, j
    cdef float total_trust
    
    for i in range(num_agents):
        total_trust = 0.0
        for j in range(num_agents):
            if i != j:
                total_trust += interaction_history[i, j]
        trust_scores_out[i] = total_trust / <float>(num_agents - 1)


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int detect_byzantine_failure(
    float[:] agent_values,
    int num_agents,
    float anomaly_threshold
) nogil:
    """
    Detect Byzantine failure (outlier agent).
    
    Args:
        agent_values: (N,) reported values from agents
        num_agents: number of agents
        anomaly_threshold: deviation threshold (in standard deviations)
        
    Returns:
        agent_index: index of Byzantine agent, or -1 if none
    """
    cdef Py_ssize_t i
    cdef float mean = 0.0
    cdef float variance = 0.0
    cdef float std_dev
    cdef float deviation
    
    # Compute mean
    for i in range(num_agents):
        mean += agent_values[i]
    mean /= <float>num_agents
    
    # Compute variance
    for i in range(num_agents):
        deviation = agent_values[i] - mean
        variance += deviation * deviation
    variance /= <float>num_agents
    std_dev = sqrt(variance)
    
    # Detect outlier
    for i in range(num_agents):
        if fabs(agent_values[i] - mean) > anomaly_threshold * std_dev:
            return i
    
    return -1


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void gossip_propagation_step(
    float[:] agent_states,
    float[:, :] adjacency_matrix,
    int num_agents,
    float mixing_rate,
    float[:] new_states_out
) nogil:
    """
    One step of gossip protocol (epidemic information spread).
    
    Args:
        agent_states: (N,) current agent states
        adjacency_matrix: (N, N) communication graph
        num_agents: number of agents
        mixing_rate: how much to mix with neighbors [0, 1]
        new_states_out: (N,) updated states
    """
    cdef Py_ssize_t i, j
    cdef float neighbor_sum
    cdef int neighbor_count
    
    for i in range(num_agents):
        neighbor_sum = 0.0
        neighbor_count = 0
        
        for j in range(num_agents):
            if i != j and adjacency_matrix[i, j] > 0.0:
                neighbor_sum += agent_states[j]
                neighbor_count += 1
        
        if neighbor_count > 0:
            new_states_out[i] = (1.0 - mixing_rate) * agent_states[i] + \
                                mixing_rate * (neighbor_sum / <float>neighbor_count)
        else:
            new_states_out[i] = agent_states[i]


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int compute_consensus_round_raft(
    int[:] agent_term_numbers,
    int[:] agent_vote_for,
    int candidate_id,
    int num_agents
) nogil:
    """
    RAFT consensus: check if candidate wins election.
    
    Args:
        agent_term_numbers: (N,) current term numbers
        agent_vote_for: (N,) who each agent voted for (-1 if none)
        candidate_id: ID of candidate checking for victory
        num_agents: number of agents
        
    Returns:
        1 if candidate wins, 0 otherwise
    """
    cdef Py_ssize_t i
    cdef int votes_received = 0
    cdef int current_term = agent_term_numbers[candidate_id]
    
    for i in range(num_agents):
        if agent_term_numbers[i] == current_term and agent_vote_for[i] == candidate_id:
            votes_received += 1
    
    if votes_received > num_agents / 2:
        return 1
    return 0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_paxos_proposal_numbers(
    int[:] agent_last_seen,
    int proposer_id,
    int num_agents,
    int[:] proposal_number_out
) nogil:
    """
    Generate Paxos proposal number (higher than all seen).
    
    Args:
        agent_last_seen: (N,) last proposal numbers seen by agents
        proposer_id: ID of proposing agent
        num_agents: number of agents
        proposal_number_out: (1,) new proposal number
    """
    cdef Py_ssize_t i
    cdef int max_seen = 0
    
    for i in range(num_agents):
        if agent_last_seen[i] > max_seen:
            max_seen = agent_last_seen[i]
    
    proposal_number_out[0] = max_seen + 1


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float compute_network_partition_score(
    float[:, :] connectivity_matrix,
    int num_agents
) nogil:
    """
    Estimate network partition risk (connectivity score).
    
    Args:
        connectivity_matrix: (N, N) link strengths
        num_agents: number of agents
        
    Returns:
        partition_risk: [0, 1], 1 = high risk
    """
    cdef Py_ssize_t i, j
    cdef float total_connectivity = 0.0
    cdef float max_connectivity = <float>(num_agents * (num_agents - 1))
    
    for i in range(num_agents):
        for j in range(num_agents):
            if i != j:
                total_connectivity += connectivity_matrix[i, j]
    
    return 1.0 - (total_connectivity / max_connectivity)


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_vector_clock_update(
    int[:] local_clock,
    int[:] received_clock,
    int agent_id,
    int num_agents,
    int[:] updated_clock_out
) nogil:
    """
    Update vector clock on message receive (Lamport clocks).
    
    Args:
        local_clock: (N,) local vector clock
        received_clock: (N,) received vector clock
        agent_id: ID of receiving agent
        num_agents: number of agents
        updated_clock_out: (N,) updated vector clock
    """
    cdef Py_ssize_t i
    
    for i in range(num_agents):
        if local_clock[i] > received_clock[i]:
            updated_clock_out[i] = local_clock[i]
        else:
            updated_clock_out[i] = received_clock[i]
    
    # Increment own clock
    updated_clock_out[agent_id] += 1


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int detect_causal_ordering_violation(
    int[:] event1_clock,
    int[:] event2_clock,
    int num_agents
) nogil:
    """
    Check if event2 causally depends on event1 (vector clock comparison).
    
    Args:
        event1_clock: (N,) vector clock of first event
        event2_clock: (N,) vector clock of second event
        num_agents: number of agents
        
    Returns:
        1 if event1 happens-before event2, 0 otherwise
    """
    cdef Py_ssize_t i
    cdef int all_leq = 1
    cdef int at_least_one_lt = 0
    
    for i in range(num_agents):
        if event1_clock[i] > event2_clock[i]:
            all_leq = 0
            break
        if event1_clock[i] < event2_clock[i]:
            at_least_one_lt = 1
    
    if all_leq and at_least_one_lt:
        return 1
    return 0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void aggregate_agent_beliefs_bayesian(
    float[:, :] agent_probability_distributions,
    int num_agents,
    int num_outcomes,
    float[:] aggregated_distribution_out
) nogil:
    """
    Aggregate agent beliefs using Bayesian fusion.
    
    Args:
        agent_probability_distributions: (N, K) each agent's distribution over K outcomes
        num_agents: number of agents
        num_outcomes: number of possible outcomes
        aggregated_distribution_out: (K,) aggregated distribution
    """
    cdef Py_ssize_t i, k
    cdef float log_product
    cdef float normalizer = 0.0
    
    # Log-linear pooling (geometric mean)
    for k in range(num_outcomes):
        log_product = 0.0
        for i in range(num_agents):
            if agent_probability_distributions[i, k] > 1e-8:
                log_product += log(agent_probability_distributions[i, k])
        aggregated_distribution_out[k] = exp(log_product / <float>num_agents)
        normalizer += aggregated_distribution_out[k]
    
    # Normalize
    for k in range(num_outcomes):
        aggregated_distribution_out[k] /= normalizer


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float compute_consensus_convergence_rate(
    float[:] current_states,
    float[:] previous_states,
    int num_agents
) nogil:
    """
    Compute convergence rate of consensus algorithm.
    
    Args:
        current_states: (N,) current agent states
        previous_states: (N,) previous agent states
        num_agents: number of agents
        
    Returns:
        convergence_rate: change magnitude [0, inf]
    """
    cdef Py_ssize_t i
    cdef float total_change = 0.0
    cdef float delta
    
    for i in range(num_agents):
        delta = current_states[i] - previous_states[i]
        total_change += delta * delta
    
    return sqrt(total_change / <float>num_agents)


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void select_agents_by_reputation(
    float[:] reputation_scores,
    int num_to_select,
    int[:] selected_agents_out
) nogil:
    """
    Select agents probabilistically by reputation for task assignment.
    
    Args:
        reputation_scores: (N,) agent reputations [0, 1]
        num_to_select: k agents to select
        selected_agents_out: (k,) selected agent indices
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t N = reputation_scores.shape[0]
    cdef float total_reputation = 0.0
    cdef float cumulative, threshold
    cdef int selected[1000]
    
    # Initialize
    for i in range(1000):
        selected[i] = 0
    
    # Compute total
    for i in range(N):
        total_reputation += reputation_scores[i]
    
    # Stochastic selection
    for i in range(num_to_select):
        threshold = (<float>rand() / <float>RAND_MAX) * total_reputation
        cumulative = 0.0
        
        for j in range(N):
            if selected[j] == 0:
                cumulative += reputation_scores[j]
                if cumulative >= threshold:
                    selected[j] = 1
                    selected_agents_out[i] = j
                    total_reputation -= reputation_scores[j]
                    break
