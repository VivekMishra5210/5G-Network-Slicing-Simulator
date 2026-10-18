"""
MCRA (Minimum Cost Resource Allocation) Cost Functions and Algorithmic Core.

Reference:
Jia-You Lin, Ping-Hung Chou, Ren-Hung Hwang,
"Dynamic Resource Allocation for Network Slicing with Multi-Tenants in 5G Two-Tier Networks,"
Sensors, 23(10), 4698 (2023). DOI: 10.3390/s23104698
"""

import math
from typing import Dict, List, Tuple, Optional, Any
from mcra.models import ResourceType


def node_exponential_cost(
    usage: float,
    capacity: float,
    cost_base: float = 2.0,
) -> float:
    """
    Compute the convex exponential cost of resource occupancy at a node or link.
    Formula: C(u) = delta ^ (u / M - 1)
    where:
      - u: current allocated / occupied resource usage
      - M: maximum capacity of the node or link
      - delta: cost base parameter (delta > 1.0)
    """
    if capacity <= 0:
        raise ValueError(f"Capacity M must be strictly positive, got {capacity}")
    if cost_base <= 1.0:
        raise ValueError(f"Cost base delta must be strictly greater than 1.0, got {cost_base}")
    if usage < -1e-9:
        raise ValueError(f"Usage cannot be negative, got {usage}")

    # Clamp usage within [0, capacity] to guard against tiny float noise
    normalized_usage = max(0.0, min(1.0, usage / capacity))
    exponent = normalized_usage - 1.0
    return math.pow(cost_base, exponent)


def marginal_cost(
    used_before: float,
    increment: float,
    capacity: float,
    cost_base: float = 2.0,
) -> float:
    """
    Compute the marginal cost gamma(u, Delta_u, M) of adding a resource increment Delta_u.
    Formula: gamma = C(u + Delta_u) - C(u) = delta ^ ((u + Delta_u)/M - 1) - delta ^ (u/M - 1)

    Properties:
    - gamma >= 0 for all legal increments
    - Strictly convex: adding an increment to a heavily loaded node incurs a much higher marginal cost
    - Rejects invalid parameters or increments that exceed maximum capacity
    """
    if capacity <= 0:
        raise ValueError(f"Capacity M must be strictly positive, got {capacity}")
    if increment <= 0:
        raise ValueError(f"Increment Delta_u must be strictly positive, got {increment}")
    if cost_base <= 1.0:
        raise ValueError(f"Cost base delta must be strictly greater than 1.0, got {cost_base}")
    if used_before < -1e-9:
        raise ValueError(f"Used before cannot be negative, got {used_before}")
    if used_before + increment > capacity + 1e-9:
        raise ValueError(
            f"Total usage (used_before={used_before} + increment={increment} = {used_before + increment}) "
            f"exceeds maximum capacity M={capacity}"
        )

    cost_before = node_exponential_cost(used_before, capacity, cost_base)
    cost_after = node_exponential_cost(used_before + increment, capacity, cost_base)

    marginal = cost_after - cost_before
    return max(0.0, marginal)
