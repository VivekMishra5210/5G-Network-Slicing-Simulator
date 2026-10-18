"""
Unit tests for physical latency components, serialization, propagation, and E2E delay.
"""

import pytest
from mcra.models import CommunicationLink, ComputeNode, Route, NodeTier
from mcra.latency import (
    mbps_to_bits_per_ms,
    serialization_delay_ms,
    propagation_delay_ms,
    compute_delay_ms,
    predict_route_e2e_delay_ms,
    calculate_latency_breakdown,
)


def test_unit_conversion_mbps_to_bits_per_ms():
    """1 Mbps must equal 1,000 bits per millisecond."""
    assert mbps_to_bits_per_ms(1.0) == 1000.0
    assert mbps_to_bits_per_ms(50.0) == 50000.0
    assert mbps_to_bits_per_ms(100.0) == 100000.0


def test_serialization_delay_calculation():
    """
    Payload = 12,000 bits (1,500 bytes).
    Link rate = 10 Mbps = 10,000 bits/ms.
    Serialization delay = 12,000 / 10,000 = 1.2 ms.
    """
    payload_bits = 12000.0
    link_rate_mbps = 10.0
    delay = serialization_delay_ms(payload_bits, link_rate_mbps)
    assert pytest.approx(delay, rel=1e-5) == 1.2


def test_compute_delay_calculation():
    """
    Compute demand = 10 units.
    Allocated rate = 5 units/ms. Base delay = 1 ms.
    Total compute delay = (10 / 5) + 1 = 3 ms.
    """
    delay = compute_delay_ms(compute_demand=10.0, allocated_compute_rate=5.0, base_delay_ms=1.0)
    assert pytest.approx(delay, rel=1e-5) == 3.0


def test_end_to_end_route_delay_sum():
    """
    Verify E2E delay across a route:
    Link 1: 10 Mbps, 0.5 ms prop
    Link 2: 20 Mbps, 1.0 ms prop
    Compute Node: 5 units/ms, 0.5 ms base
    Payload = 10,000 bits. Compute demand = 10 units.

    Link 1 Ser = 10,000 / 10,000 = 1.0 ms + 0.5 prop = 1.5 ms.
    Link 2 Ser = 10,000 / 20,000 = 0.5 ms + 1.0 prop = 1.5 ms.
    Compute = (10 / 5) + 0.5 = 2.5 ms.
    Total E2E = 1.5 + 1.5 + 2.5 = 5.5 ms.
    """
    l1 = CommunicationLink("l1", "ue", "edge_router", capacity_mbps=100.0, propagation_delay_ms=0.5)
    l2 = CommunicationLink("l2", "edge_router", "edge", capacity_mbps=100.0, propagation_delay_ms=1.0)
    c1 = ComputeNode("c1", NodeTier.EDGE, capacity_units=50.0, base_delay_ms=0.5)

    route = Route("r_test", "edge", links=[l1, l2], compute_node=c1)

    allocations = {"l1": 10.0, "l2": 20.0, "c1": 5.0}

    pred_delay = predict_route_e2e_delay_ms(
        payload_bits=10000.0,
        compute_demand=10.0,
        route=route,
        allocations=allocations,
        estimated_queue_delay_ms=0.0,
    )
    assert pytest.approx(pred_delay, rel=1e-5) == 5.5

    breakdown = calculate_latency_breakdown(
        payload_bits=10000.0,
        compute_demand=10.0,
        route=route,
        allocations=allocations,
        measured_queue_delay_ms=0.0,
    )
    assert breakdown["total_e2e_delay_ms"] == 5.5
    assert breakdown["serialization_delay_ms"] == 1.5
    assert breakdown["propagation_delay_ms"] == 1.5
    assert breakdown["compute_delay_ms"] == 2.5
