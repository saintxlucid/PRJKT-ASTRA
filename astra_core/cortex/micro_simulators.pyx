# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True
# distutils: language = c
"""
🔮 ASTRA Micro-Simulators — Predictive Engines (Cython Acceleration)

Fast simulation kernels at C-speed:
- Economic micro-models (supply/demand)
- Social dynamics (opinion diffusion, network effects)
- Logistics optimization (routing, scheduling)
- Resource allocation
- Time-series forecasting primitives
- Monte Carlo sampling

Think of this as ASTRA's "simulation laboratory" for rapid predictions.
"""

import numpy as np
cimport numpy as cnp
cimport cython
from libc.math cimport exp, log, sqrt, fabs, pow, tanh, sin, cos
from libc.stdlib cimport rand, RAND_MAX

cnp.import_array()


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void simulate_supply_demand(
    float price,
    float supply_elasticity,
    float demand_elasticity,
    float shock,
    float[:] equilibrium_out
) nogil:
    """
    Simulate supply-demand equilibrium with price shock.
    
    Args:
        price: current price
        supply_elasticity: supply response to price
        demand_elasticity: demand response to price (negative)
        shock: external shock magnitude
        equilibrium_out: (3,) [new_price, new_supply, new_demand]
    """
    cdef float supply = price * supply_elasticity
    cdef float demand = price * demand_elasticity
    cdef float excess = supply - demand + shock
    cdef float price_adjustment = -0.1 * excess  # Price adjusts to clear market
    cdef float new_price = price + price_adjustment
    
    if new_price < 0.01:
        new_price = 0.01  # Floor
    
    equilibrium_out[0] = new_price
    equilibrium_out[1] = new_price * supply_elasticity
    equilibrium_out[2] = new_price * demand_elasticity


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void diffuse_opinions(
    float[:] opinions,
    float[:, :] adjacency,
    float diffusion_rate,
    float[:] opinions_out
) nogil:
    """
    Simulate opinion diffusion on social network.
    
    Opinions spread between connected nodes (heat equation on graph).
    
    Args:
        opinions: (N,) current opinion values (-1 to +1)
        adjacency: (N, N) adjacency matrix (0 or 1)
        diffusion_rate: speed of opinion spread
        opinions_out: (N,) updated opinions
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t N = opinions.shape[0]
    cdef float neighbor_opinion, degree, opinion_delta
    
    for i in range(N):
        neighbor_opinion = 0.0
        degree = 0.0
        
        # Average neighbor opinions
        for j in range(N):
            if adjacency[i, j] > 0.5:
                neighbor_opinion += opinions[j]
                degree += 1.0
        
        if degree > 0.0:
            neighbor_opinion /= degree
            opinion_delta = diffusion_rate * (neighbor_opinion - opinions[i])
            opinions_out[i] = opinions[i] + opinion_delta
        else:
            opinions_out[i] = opinions[i]
        
        # Clamp to [-1, 1]
        if opinions_out[i] < -1.0:
            opinions_out[i] = -1.0
        elif opinions_out[i] > 1.0:
            opinions_out[i] = 1.0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float optimize_route_greedy(
    float[:, :] distance_matrix,
    int start_node,
    int[:] route_out
) nogil:
    """
    Greedy nearest-neighbor TSP approximation.
    
    Args:
        distance_matrix: (N, N) pairwise distances
        start_node: starting node index
        route_out: (N,) output route
        
    Returns:
        total_distance: route length
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t N = distance_matrix.shape[0]
    cdef int current = start_node
    cdef float total_distance = 0.0
    cdef float min_distance, dist
    cdef int next_node
    cdef int visited[256]  # Max 256 nodes
    
    # Initialize
    for i in range(256):
        visited[i] = 0
    
    route_out[0] = current
    visited[current] = 1
    
    # Greedy selection
    for i in range(1, N):
        min_distance = 1e9
        next_node = current
        
        for j in range(N):
            if visited[j] == 0:
                dist = distance_matrix[current, j]
                if dist < min_distance:
                    min_distance = dist
                    next_node = j
        
        route_out[i] = next_node
        visited[next_node] = 1
        total_distance += min_distance
        current = next_node
    
    # Return to start
    total_distance += distance_matrix[current, start_node]
    
    return total_distance


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void allocate_resources(
    float[:] demands,
    float[:] capacities,
    float[:] allocations_out
) nogil:
    """
    Allocate scarce resources proportionally to demands.
    
    Args:
        demands: (N,) resource demands
        capacities: (N,) resource capacities
        allocations_out: (N,) allocated amounts
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = demands.shape[0]
    cdef float total_demand = 0.0
    cdef float total_capacity = 0.0
    cdef float allocation_ratio
    
    # Compute totals
    for i in range(N):
        total_demand += demands[i]
        total_capacity += capacities[i]
    
    # Proportional allocation
    if total_demand > 0.0:
        allocation_ratio = total_capacity / total_demand
        if allocation_ratio > 1.0:
            allocation_ratio = 1.0  # Can satisfy all demands
        
        for i in range(N):
            allocations_out[i] = demands[i] * allocation_ratio
            
            # Respect individual capacity constraints
            if allocations_out[i] > capacities[i]:
                allocations_out[i] = capacities[i]
    else:
        for i in range(N):
            allocations_out[i] = 0.0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void forecast_ar1(
    float[:] history,
    float phi,
    float sigma,
    int horizon,
    float[:] forecast_out
) nogil:
    """
    AR(1) time series forecast.
    
    x_t = phi * x_{t-1} + epsilon_t
    
    Args:
        history: (T,) historical values
        phi: autoregressive coefficient
        sigma: noise standard deviation
        horizon: forecast steps
        forecast_out: (horizon,) forecasted values
    """
    cdef Py_ssize_t t
    cdef Py_ssize_t T = history.shape[0]
    cdef float last_value = history[T - 1]
    cdef float forecast, noise
    
    for t in range(horizon):
        # Simple forecast without noise (mean prediction)
        forecast = phi * last_value
        
        # Could add noise for stochastic forecast
        # noise = sigma * randn()
        # forecast += noise
        
        forecast_out[t] = forecast
        last_value = forecast


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void simulate_sir_epidemic(
    float[:] state,
    float beta,
    float gamma,
    float dt,
    float[:] state_out
) nogil:
    """
    SIR epidemic model simulation step.
    
    S: susceptible, I: infected, R: recovered
    dS/dt = -beta * S * I
    dI/dt = beta * S * I - gamma * I
    dR/dt = gamma * I
    
    Args:
        state: (3,) [S, I, R] current state
        beta: infection rate
        gamma: recovery rate
        dt: time step
        state_out: (3,) next state
    """
    cdef float S = state[0]
    cdef float I = state[1]
    cdef float R = state[2]
    
    cdef float dS = -beta * S * I * dt
    cdef float dI = (beta * S * I - gamma * I) * dt
    cdef float dR = gamma * I * dt
    
    state_out[0] = S + dS
    state_out[1] = I + dI
    state_out[2] = R + dR
    
    # Ensure non-negative
    if state_out[0] < 0.0:
        state_out[0] = 0.0
    if state_out[1] < 0.0:
        state_out[1] = 0.0
    if state_out[2] < 0.0:
        state_out[2] = 0.0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void monte_carlo_sample(
    float[:] distribution,
    int num_samples,
    int[:] samples_out
) nogil:
    """
    Monte Carlo sampling from discrete distribution.
    
    Args:
        distribution: (K,) probability distribution (sums to 1)
        num_samples: number of samples to draw
        samples_out: (num_samples,) sampled indices
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t K = distribution.shape[0]
    cdef float rand_val, cumsum
    
    for i in range(num_samples):
        rand_val = <float>rand() / <float>RAND_MAX
        cumsum = 0.0
        
        for j in range(K):
            cumsum += distribution[j]
            if rand_val <= cumsum:
                samples_out[i] = j
                break


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float compute_expected_value(
    float[:] outcomes,
    float[:] probabilities
) nogil:
    """
    Compute expected value of discrete random variable.
    
    Args:
        outcomes: (K,) possible outcome values
        probabilities: (K,) probabilities (sum to 1)
        
    Returns:
        expected_value: E[X]
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t K = outcomes.shape[0]
    cdef float expected = 0.0
    
    for i in range(K):
        expected += outcomes[i] * probabilities[i]
    
    return expected


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void simulate_queue_dynamics(
    float arrival_rate,
    float service_rate,
    float dt,
    int num_steps,
    float[:] queue_length_out
) nogil:
    """
    M/M/1 queue simulation.
    
    Args:
        arrival_rate: customers per time unit
        service_rate: customers served per time unit
        dt: time step
        num_steps: simulation steps
        queue_length_out: (num_steps,) queue length over time
    """
    cdef Py_ssize_t t
    cdef float queue = 0.0
    cdef float arrivals, departures, rand_val
    
    for t in range(num_steps):
        # Poisson arrivals (approximation)
        rand_val = <float>rand() / <float>RAND_MAX
        if rand_val < arrival_rate * dt:
            arrivals = 1.0
        else:
            arrivals = 0.0
        
        # Service (if queue non-empty)
        if queue > 0.0:
            rand_val = <float>rand() / <float>RAND_MAX
            if rand_val < service_rate * dt:
                departures = 1.0
            else:
                departures = 0.0
        else:
            departures = 0.0
        
        queue += arrivals - departures
        
        if queue < 0.0:
            queue = 0.0
        
        queue_length_out[t] = queue


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_network_centrality(
    float[:, :] adjacency,
    float[:] centrality_out
) nogil:
    """
    Compute degree centrality for social network.
    
    Args:
        adjacency: (N, N) adjacency matrix
        centrality_out: (N,) centrality scores
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t N = adjacency.shape[0]
    cdef float degree
    
    for i in range(N):
        degree = 0.0
        for j in range(N):
            if adjacency[i, j] > 0.5:
                degree += 1.0
        
        centrality_out[i] = degree / (<float>N - 1.0) if N > 1 else 0.0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void optimize_portfolio(
    float[:] returns,
    float[:] risks,
    float risk_tolerance,
    float[:] weights_out
) nogil:
    """
    Simple portfolio optimization (mean-variance approximation).
    
    Args:
        returns: (N,) expected returns
        risks: (N,) standard deviations
        risk_tolerance: risk aversion parameter
        weights_out: (N,) portfolio weights (sum to 1)
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = returns.shape[0]
    cdef float utility, total_utility = 0.0
    
    # Compute utility scores
    for i in range(N):
        utility = returns[i] - risk_tolerance * risks[i] * risks[i]
        if utility < 0.0:
            utility = 0.0
        weights_out[i] = utility
        total_utility += utility
    
    # Normalize to sum to 1
    if total_utility > 0.0:
        for i in range(N):
            weights_out[i] /= total_utility
    else:
        # Equal weights fallback
        for i in range(N):
            weights_out[i] = 1.0 / <float>N


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float simulate_nash_equilibrium(
    float[:, :] payoff_matrix_a,
    float[:, :] payoff_matrix_b,
    float[:] strategy_a,
    float[:] strategy_b,
    float learning_rate,
    int iterations
) nogil:
    """
    Iterative Nash equilibrium approximation (fictitious play).
    
    Args:
        payoff_matrix_a: (M, N) player A payoffs
        payoff_matrix_b: (M, N) player B payoffs
        strategy_a: (M,) player A strategy (in/out)
        strategy_b: (N,) player B strategy (in/out)
        learning_rate: adaptation speed
        iterations: number of iterations
        
    Returns:
        convergence_metric: final strategy change magnitude
    """
    cdef Py_ssize_t t, i, j
    cdef Py_ssize_t M = payoff_matrix_a.shape[0]
    cdef Py_ssize_t N = payoff_matrix_a.shape[1]
    cdef float best_response_a, best_response_b
    cdef float payoff, total_a = 0.0, total_b = 0.0
    cdef float convergence = 0.0
    
    for t in range(iterations):
        # Best response for player A
        best_response_a = 0.0
        for i in range(M):
            payoff = 0.0
            for j in range(N):
                payoff += payoff_matrix_a[i, j] * strategy_b[j]
            
            if payoff > best_response_a:
                best_response_a = payoff
        
        # Update strategy A
        total_a = 0.0
        for i in range(M):
            strategy_a[i] += learning_rate * (1.0 / <float>M - strategy_a[i])
            total_a += strategy_a[i]
        
        # Normalize
        for i in range(M):
            strategy_a[i] /= total_a
        
        # Best response for player B
        best_response_b = 0.0
        for j in range(N):
            payoff = 0.0
            for i in range(M):
                payoff += payoff_matrix_b[i, j] * strategy_a[i]
            
            if payoff > best_response_b:
                best_response_b = payoff
        
        # Update strategy B
        total_b = 0.0
        for j in range(N):
            strategy_b[j] += learning_rate * (1.0 / <float>N - strategy_b[j])
            total_b += strategy_b[j]
        
        # Normalize
        for j in range(N):
            strategy_b[j] /= total_b
    
    # Convergence metric (strategy stability)
    convergence = fabs(best_response_a - best_response_b)
    return convergence


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void simulate_brownian_motion(
    float x0,
    float mu,
    float sigma,
    float dt,
    int num_steps,
    float[:] trajectory_out
) nogil:
    """
    Geometric Brownian motion simulation (stock prices, etc.).
    
    dX = mu * X * dt + sigma * X * dW
    
    Args:
        x0: initial value
        mu: drift
        sigma: volatility
        dt: time step
        num_steps: number of steps
        trajectory_out: (num_steps,) simulated trajectory
    """
    cdef Py_ssize_t t
    cdef float x = x0
    cdef float dW, rand1, rand2
    
    trajectory_out[0] = x
    
    for t in range(1, num_steps):
        # Box-Muller for Gaussian noise
        rand1 = <float>rand() / <float>RAND_MAX
        rand2 = <float>rand() / <float>RAND_MAX
        dW = sqrt(-2.0 * log(rand1 + 1e-10)) * cos(6.28318530718 * rand2)
        
        x = x + mu * x * dt + sigma * x * sqrt(dt) * dW
        
        if x < 0.0:
            x = 0.0  # Floor at zero
        
        trajectory_out[t] = x
