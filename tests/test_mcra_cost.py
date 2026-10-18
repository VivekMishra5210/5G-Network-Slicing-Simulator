"""
Unit tests for MCRA marginal cost function and convexity verification.
"""

import math
import pytest
from allocators.mcra_allocator import node_exponential_cost, marginal_cost


def test_marginal_cost_hand_calculated_example():
    """
    Verify marginal cost against an exact hand-calculated analytical example.
    Let capacity M = 100, cost_base delta = 2.0.
    Let used_before u = 0, increment Delta_u = 50.
    C(0) = 2^(0/100 - 1) = 2^(-1) = 0.5.
    C(50) = 2^(50/100 - 1) = 2^(-0.5) = 1 / sqrt(2) approx 0.70710678.
    gamma = C(50) - C(0) approx 0.20710678.
    """
    M = 100.0
    delta = 2.0
    u = 0.0
    inc = 50.0

    expected_cost_before = 0.5
    expected_cost_after = 1.0 / math.sqrt(2.0)
    expected_gamma = expected_cost_after - expected_cost_before

    actual_gamma = marginal_cost(u, inc, M, delta)
    assert pytest.approx(actual_gamma, rel=1e-5) == expected_gamma


def test_marginal_cost_convexity_increase():
    """
    Marginal cost must increase as current resource occupancy increases.
    Adding 10 units at 10% load must be strictly cheaper than adding 10 units at 80% load.
    """
    M = 100.0
    inc = 10.0
    delta = 2.0

    cost_at_low_load = marginal_cost(10.0, inc, M, delta)
    cost_at_med_load = marginal_cost(50.0, inc, M, delta)
    cost_at_high_load = marginal_cost(80.0, inc, M, delta)

    assert cost_at_low_load > 0
    assert cost_at_med_load > cost_at_low_load
    assert cost_at_high_load > cost_at_med_load


def test_marginal_cost_rejects_over_capacity():
    """Attempting an increment that exceeds capacity must raise ValueError."""
    M = 100.0
    with pytest.raises(ValueError, match="exceeds maximum capacity"):
        marginal_cost(95.0, 10.0, M, 2.0)


def test_marginal_cost_rejects_invalid_parameters():
    """Zero/negative capacities, non-positive increments, or delta <= 1 must raise ValueError."""
    # Capacity <= 0
    with pytest.raises(ValueError, match="Capacity M must be strictly positive"):
        marginal_cost(0.0, 5.0, 0.0, 2.0)

    # Increment <= 0
    with pytest.raises(ValueError, match="Increment Delta_u must be strictly positive"):
        marginal_cost(10.0, 0.0, 100.0, 2.0)

    # Cost base <= 1
    with pytest.raises(ValueError, match="Cost base delta must be strictly greater than 1.0"):
        marginal_cost(10.0, 5.0, 100.0, 1.0)
