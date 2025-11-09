# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True
# distutils: language = c
"""
🧠 ASTRA Neural Router — Hive-Mind Orchestrator (Cython Acceleration)

Multi-model orchestration at C-speed:
- GPT-OSS 20B routing
- Multiple local LLMs (Arabic + English)
- Agent voting & consensus
- Dynamic load balancing
- Confidence-based delegation
- Fallback chains

Think of this as ASTRA's "frontal cortex" for multi-agent decision-making.
"""

import numpy as np
cimport numpy as cnp
cimport cython
from libc.math cimport exp, log, sqrt, fabs
from libc.stdlib cimport rand, RAND_MAX

cnp.import_array()


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_routing_scores(
    float[:, :] agent_embeddings,
    float[:] query_embedding,
    float[:] confidence_scores,
    float[:] routing_scores_out,
    float temperature=1.0
) nogil:
    """
    Compute routing scores for multi-agent delegation.
    
    Score = softmax((agent · query) / sqrt(dim) / temperature) * confidence
    
    Args:
        agent_embeddings: (num_agents, dim) agent capability embeddings
        query_embedding: (dim,) query embedding
        confidence_scores: (num_agents,) current agent confidence levels
        routing_scores_out: (num_agents,) output routing scores
        temperature: softmax temperature for sharpening/smoothing
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t num_agents = agent_embeddings.shape[0]
    cdef Py_ssize_t dim = agent_embeddings.shape[1]
    cdef float dot_product, max_score, score_sum
    cdef float dim_scale = 1.0 / sqrt(<float>dim)
    
    # Compute raw scores (scaled dot products)
    max_score = -1e9
    for i in range(num_agents):
        dot_product = 0.0
        for j in range(dim):
            dot_product += agent_embeddings[i, j] * query_embedding[j]
        
        routing_scores_out[i] = dot_product * dim_scale / temperature
        if routing_scores_out[i] > max_score:
            max_score = routing_scores_out[i]
    
    # Softmax (numerically stable)
    score_sum = 0.0
    for i in range(num_agents):
        routing_scores_out[i] = exp(routing_scores_out[i] - max_score)
        score_sum += routing_scores_out[i]
    
    # Normalize and weight by confidence
    for i in range(num_agents):
        routing_scores_out[i] = (routing_scores_out[i] / score_sum) * confidence_scores[i]


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int select_best_agent(
    float[:] routing_scores,
    float[:] load_factors,
    float load_penalty=0.3
) nogil:
    """
    Select best agent considering both routing score and current load.
    
    Adjusted score = routing_score * (1 - load_penalty * load_factor)
    
    Args:
        routing_scores: (num_agents,) routing scores
        load_factors: (num_agents,) current load (0=idle, 1=maxed)
        load_penalty: how much to penalize loaded agents
        
    Returns:
        agent_idx: index of selected agent
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t num_agents = routing_scores.shape[0]
    cdef float adjusted_score, best_score = -1e9
    cdef int best_agent = 0
    
    for i in range(num_agents):
        adjusted_score = routing_scores[i] * (1.0 - load_penalty * load_factors[i])
        if adjusted_score > best_score:
            best_score = adjusted_score
            best_agent = i
    
    return best_agent


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_agent_consensus(
    float[:, :] agent_votes,
    float[:] agent_weights,
    float[:] consensus_out,
    float agreement_threshold=0.7
) nogil:
    """
    Compute weighted consensus from multiple agent votes.
    
    Used when multiple agents process same query (voting ensemble).
    
    Args:
        agent_votes: (num_agents, num_options) vote distributions
        agent_weights: (num_agents,) agent credibility weights
        consensus_out: (num_options,) weighted consensus distribution
        agreement_threshold: minimum agreement level (0-1)
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t num_agents = agent_votes.shape[0]
    cdef Py_ssize_t num_options = agent_votes.shape[1]
    cdef float total_weight = 0.0
    cdef float max_consensus = 0.0
    cdef float agreement
    
    # Weighted sum
    for j in range(num_options):
        consensus_out[j] = 0.0
    
    for i in range(num_agents):
        total_weight += agent_weights[i]
    
    for i in range(num_agents):
        for j in range(num_options):
            consensus_out[j] += agent_votes[i, j] * agent_weights[i]
    
    # Normalize
    if total_weight > 0.0:
        for j in range(num_options):
            consensus_out[j] /= total_weight
            if consensus_out[j] > max_consensus:
                max_consensus = consensus_out[j]
    
    # Check agreement level
    agreement = max_consensus
    if agreement < agreement_threshold:
        # Low agreement — flatten distribution (uncertainty signal)
        for j in range(num_options):
            consensus_out[j] = 1.0 / <float>num_options


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void update_agent_confidence(
    float[:] confidence_scores,
    float[:] success_indicators,
    float[:] response_times,
    float alpha=0.1,
    float time_penalty=0.01
) nogil:
    """
    Update agent confidence scores based on recent performance.
    
    Confidence decay on failure, boost on success.
    Also penalizes slow responses (quality/latency tradeoff).
    
    Args:
        confidence_scores: (num_agents,) current confidence (in-place update)
        success_indicators: (num_agents,) 1.0=success, 0.0=failure
        response_times: (num_agents,) response time in seconds
        alpha: learning rate for confidence updates
        time_penalty: penalty per second of response time
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t num_agents = confidence_scores.shape[0]
    cdef float target_confidence, time_factor
    
    for i in range(num_agents):
        # Target confidence based on success
        target_confidence = success_indicators[i]
        
        # Time penalty (slower responses reduce confidence)
        time_factor = 1.0 - time_penalty * response_times[i]
        if time_factor < 0.1:
            time_factor = 0.1  # Floor
        
        target_confidence *= time_factor
        
        # Exponential moving average
        confidence_scores[i] += alpha * (target_confidence - confidence_scores[i])
        
        # Clamp to [0, 1]
        if confidence_scores[i] < 0.0:
            confidence_scores[i] = 0.0
        elif confidence_scores[i] > 1.0:
            confidence_scores[i] = 1.0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_fallback_chain(
    float[:] routing_scores,
    int[:] fallback_chain_out,
    int max_fallbacks=3
) nogil:
    """
    Compute fallback chain (ordered list of agents to try).
    
    Used for graceful degradation when primary agent fails.
    
    Args:
        routing_scores: (num_agents,) routing scores
        fallback_chain_out: (max_fallbacks,) output agent indices (sorted by score)
        max_fallbacks: maximum fallback depth
    """
    cdef Py_ssize_t i, j, rank
    cdef Py_ssize_t num_agents = routing_scores.shape[0]
    cdef int best_idx
    cdef float best_score
    cdef int used[32]  # Track already selected agents (assume max 32 agents)
    
    # Initialize used flags
    for i in range(32):
        used[i] = 0
    
    # Select top k agents
    for rank in range(max_fallbacks):
        best_score = -1e9
        best_idx = 0
        
        for i in range(num_agents):
            if used[i] == 0 and routing_scores[i] > best_score:
                best_score = routing_scores[i]
                best_idx = i
        
        fallback_chain_out[rank] = best_idx
        used[best_idx] = 1


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float compute_delegation_confidence(
    float routing_score,
    float agent_confidence,
    float load_factor,
    float query_complexity
) nogil:
    """
    Compute overall confidence in delegation decision.
    
    Used to decide: delegate to agent vs. retry vs. escalate to human.
    
    Args:
        routing_score: routing score for selected agent
        agent_confidence: agent's current confidence level
        load_factor: agent's current load (0-1)
        query_complexity: estimated query difficulty (0-1)
        
    Returns:
        delegation_confidence: overall confidence (0-1)
    """
    cdef float base_confidence = routing_score * agent_confidence
    cdef float load_penalty = 0.3 * load_factor
    cdef float complexity_penalty = 0.2 * query_complexity
    cdef float confidence = base_confidence * (1.0 - load_penalty - complexity_penalty)
    
    if confidence < 0.0:
        confidence = 0.0
    elif confidence > 1.0:
        confidence = 1.0
    
    return confidence


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_load_balancing_weights(
    float[:] routing_scores,
    float[:] load_factors,
    float[:] balanced_weights_out,
    float balance_strength=0.5
) nogil:
    """
    Adjust routing scores to encourage load balancing.
    
    Higher balance_strength → more aggressive load distribution.
    
    Args:
        routing_scores: (num_agents,) raw routing scores
        load_factors: (num_agents,) current loads
        balanced_weights_out: (num_agents,) load-balanced weights
        balance_strength: 0=ignore load, 1=maximize balance
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t num_agents = routing_scores.shape[0]
    cdef float total_weight = 0.0
    cdef float load_adjustment
    
    # Compute balanced weights
    for i in range(num_agents):
        # Penalize loaded agents
        load_adjustment = 1.0 - balance_strength * load_factors[i]
        balanced_weights_out[i] = routing_scores[i] * load_adjustment
        total_weight += balanced_weights_out[i]
    
    # Normalize
    if total_weight > 0.0:
        for i in range(num_agents):
            balanced_weights_out[i] /= total_weight


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int sample_agent_stochastic(
    float[:] routing_scores,
    float temperature=1.0
) nogil:
    """
    Sample agent stochastically (exploration vs exploitation).
    
    Temperature:
    - Low (0.1): exploit best agent
    - High (2.0): explore more uniformly
    
    Args:
        routing_scores: (num_agents,) routing scores
        temperature: sampling temperature
        
    Returns:
        agent_idx: sampled agent index
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t num_agents = routing_scores.shape[0]
    cdef float cumsum = 0.0
    cdef float random_val = (<float>rand() / <float>RAND_MAX)
    cdef float max_score = -1e9
    cdef float prob_sum = 0.0
    
    # Find max for numerical stability
    for i in range(num_agents):
        if routing_scores[i] > max_score:
            max_score = routing_scores[i]
    
    # Compute softmax probabilities
    for i in range(num_agents):
        prob_sum += exp((routing_scores[i] - max_score) / temperature)
    
    # Sample using cumulative distribution
    for i in range(num_agents):
        cumsum += exp((routing_scores[i] - max_score) / temperature) / prob_sum
        if random_val <= cumsum:
            return i
    
    return num_agents - 1  # Fallback to last agent


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_specialization_affinity(
    float[:] query_features,
    float[:, :] agent_specializations,
    float[:] affinity_out
) nogil:
    """
    Compute query-agent affinity based on specialization profiles.
    
    Agents have specialization vectors (e.g., [code, math, creative, factual]).
    Queries have feature vectors matching same dimensions.
    
    Args:
        query_features: (num_features,) query feature vector
        agent_specializations: (num_agents, num_features) agent profiles
        affinity_out: (num_agents,) affinity scores
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t num_agents = agent_specializations.shape[0]
    cdef Py_ssize_t num_features = agent_specializations.shape[1]
    cdef float dot_product, query_norm = 0.0, agent_norm
    
    # Query norm
    for j in range(num_features):
        query_norm += query_features[j] * query_features[j]
    query_norm = sqrt(query_norm)
    
    # Cosine similarity
    for i in range(num_agents):
        dot_product = 0.0
        agent_norm = 0.0
        
        for j in range(num_features):
            dot_product += query_features[j] * agent_specializations[i, j]
            agent_norm += agent_specializations[i, j] * agent_specializations[i, j]
        
        agent_norm = sqrt(agent_norm)
        
        if query_norm > 0.0 and agent_norm > 0.0:
            affinity_out[i] = dot_product / (query_norm * agent_norm)
        else:
            affinity_out[i] = 0.0
