"""
Latency calculation module with explicit physical unit conversions.
Enforces standard units:
- Clock / Latency / Delays: milliseconds (ms)
- Payload: bits (1 byte = 8 bits)
- Link bandwidth: Megabits per second (Mbps) -> 1 Mbps = 1,000 bits/ms
- Compute demand: Normalized task units
- Compute processing capacity: Normalized task units per ms
"""

from typing import List, Dict, Optional
from mcra.models import CommunicationLink, ComputeNode, Route


def mbps_to_bits_per_ms(mbps: float) -> float:
    """Convert Megabits per second (Mbps) to bits per millisecond (bits/ms)."""
    # 1 Mbps = 1,000,000 bits / 1,000 ms = 1,000 bits/ms
    return float(mbps) * 1000.0


def bytes_to_bits(num_bytes: int) -> float:
    """Convert bytes to bits."""
    return float(num_bytes) * 8.0


def serialization_delay_ms(payload_bits: float, link_rate_mbps: float) -> float:
    """
    Transmission / serialization delay for a packet across a link.
    D_ser = payload_bits / (rate_mbps * 1000)
    """
    if link_rate_mbps <= 0:
        return float("inf")
    bits_per_ms = mbps_to_bits_per_ms(link_rate_mbps)
    return payload_bits / bits_per_ms


def propagation_delay_ms(link: CommunicationLink) -> float:
    """Configured physical propagation delay of the link in ms."""
    return link.propagation_delay_ms


def compute_delay_ms(
    compute_demand: float,
    allocated_compute_rate: float,
    base_delay_ms: float = 0.0,
) -> float:
    """
    Processing / compute delay at an Edge or Cloud compute node.
    D_compute = (compute_demand / allocated_compute_rate) + base_delay_ms
    """
    if allocated_compute_rate <= 0:
        return float("inf")
    return (compute_demand / allocated_compute_rate) + base_delay_ms


def predict_route_e2e_delay_ms(
    payload_bits: float,
    compute_demand: float,
    route: Route,
    allocations: Dict[str, float],
    estimated_queue_delay_ms: float = 0.0,
) -> float:
    """
    Predict end-to-end delay for a request along a candidate route under given resource allocations.
    D_pred = sum(D_ser + D_prop) + D_compute + D_queue_est
    """
    total_delay_ms = 0.0

    # 1. Traversed communication links
    for link in route.links:
        # Bandwidth assigned to this flow on this link
        link_bw = allocations.get(link.link_id, 0.0)
        if link_bw <= 0:
            return float("inf")
        d_ser = serialization_delay_ms(payload_bits, link_bw)
        d_prop = propagation_delay_ms(link)
        total_delay_ms += (d_ser + d_prop)

    # 2. Compute processing at designated node
    c_node = route.compute_node
    c_rate = allocations.get(c_node.node_id, 0.0)
    if c_rate <= 0:
        return float("inf")
    d_comp = compute_delay_ms(compute_demand, c_rate, c_node.base_delay_ms)
    total_delay_ms += d_comp

    # 3. Add estimated queuing overhead
    total_delay_ms += estimated_queue_delay_ms
    return total_delay_ms


def calculate_latency_breakdown(
    payload_bits: float,
    compute_demand: float,
    route: Route,
    allocations: Dict[str, float],
    measured_queue_delay_ms: float = 0.0,
) -> Dict[str, float]:
    """Provide an inspectable component breakdown of latency in ms."""
    total_ser = 0.0
    total_prop = 0.0

    for link in route.links:
        bw = allocations.get(link.link_id, link.capacity_mbps)
        total_ser += serialization_delay_ms(payload_bits, bw)
        total_prop += propagation_delay_ms(link)

    c_node = route.compute_node
    c_rate = allocations.get(c_node.node_id, c_node.capacity_units)
    comp_delay = compute_delay_ms(compute_demand, c_rate, c_node.base_delay_ms)

    total_e2e = measured_queue_delay_ms + total_ser + total_prop + comp_delay

    return {
        "queue_delay_ms": round(measured_queue_delay_ms, 3),
        "serialization_delay_ms": round(total_ser, 3),
        "propagation_delay_ms": round(total_prop, 3),
        "compute_delay_ms": round(comp_delay, 3),
        "total_e2e_delay_ms": round(total_e2e, 3),
    }
