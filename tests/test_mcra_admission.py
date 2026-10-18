"""
Unit tests for MCRA admission loop, reason codes, impossible QoS termination, and rollback guarantees.
"""

import pytest
from mcra.models import ServiceRequest, SliceType, RequestStatus, NodeTier, CommunicationLink, ComputeNode, Route
from mcra.resources import ResourceLedger
from mcra.topology import NetworkTopology
from mcra.allocator import MCRAAllocator


def test_mcra_admission_success_under_feasible_deadline():
    topology = NetworkTopology(access_link_capacity_mbps=100.0, edge_compute_capacity=50.0)
    ledger = ResourceLedger()
    for l in topology.all_links.values():
        ledger.register_resource(l.link_id, l.capacity_mbps, l.link_id.startswith("link") and l.capacity_mbps or 100.0)
    for n in topology.all_compute_nodes.values():
        ledger.register_resource(n.node_id, n.capacity_units, 1.0)

    allocator = MCRAAllocator(cost_base=2.0)
    routes = [topology.route_edge]

    # Feasible request: small payload, generous deadline (50 ms)
    req = ServiceRequest(
        request_id="req_test_1",
        tenant_id="tenant_1",
        ue_id="ue_1",
        slice_type=SliceType.EMBB,
        arrival_time_ms=0.0,
        payload_bits=10000.0,
        compute_demand=5.0,
        deadline_ms=50.0,
    )

    admitted, selected_route, plan, delay, trace, status = allocator.admit_request(
        req, routes, ledger, current_time_ms=0.0
    )

    assert admitted is True
    assert status == RequestStatus.ADMITTED
    assert selected_route.path_name == "edge"
    assert delay <= req.deadline_ms
    assert len(plan) > 0
    assert trace.admitted is True


def test_mcra_blocks_impossible_qos_with_reason():
    """
    If the deadline is physically impossible (e.g. 0.01 ms, which is less than physical propagation delay alone),
    the allocator must terminate safely without hanging and return a structured BLOCKED status.
    """
    topology = NetworkTopology(access_link_capacity_mbps=100.0, edge_compute_capacity=50.0)
    ledger = ResourceLedger()
    for l in topology.all_links.values():
        ledger.register_resource(l.link_id, l.capacity_mbps, 1.0)
    for n in topology.all_compute_nodes.values():
        ledger.register_resource(n.node_id, n.capacity_units, 1.0)

    # Max propagation on edge route is 0.5 + 0.2 + 0.2 = 0.9 ms.
    # A deadline of 0.1 ms is physically impossible!
    allocator = MCRAAllocator(cost_base=2.0, max_iterations=20)
    routes = [topology.route_edge]

    req = ServiceRequest(
        request_id="req_impossible",
        tenant_id="tenant_1",
        ue_id="ue_1",
        slice_type=SliceType.URLLC,
        arrival_time_ms=0.0,
        payload_bits=5000.0,
        compute_demand=5.0,
        deadline_ms=0.1,  # Impossible deadline!
    )

    admitted, _, _, _, trace, status = allocator.admit_request(
        req, routes, ledger, current_time_ms=0.0
    )

    assert admitted is False
    assert status in [RequestStatus.BLOCKED_QOS_UNSATISFIABLE, RequestStatus.BLOCKED_CAPACITY, RequestStatus.BLOCKED_SEARCH_LIMIT]
    assert trace.admitted is False

    # CRITICAL INVARIANT: Ledger must not leak resources!
    for res_id in ledger.resources.keys():
        assert ledger.get_used(res_id) == 0.0, f"Resource {res_id} leaked reservations on rejection!"


def test_mcra_blocks_when_no_route_available():
    ledger = ResourceLedger()
    allocator = MCRAAllocator()

    req = ServiceRequest(
        request_id="req_no_route",
        tenant_id="tenant_1",
        ue_id="ue_1",
        slice_type=SliceType.EMBB,
        arrival_time_ms=0.0,
        payload_bits=10000.0,
        compute_demand=5.0,
        deadline_ms=50.0,
    )

    admitted, selected_route, plan, delay, trace, status = allocator.admit_request(
        req, candidate_routes=[], ledger=ledger, current_time_ms=0.0
    )

    assert admitted is False
    assert status == RequestStatus.BLOCKED_NO_ROUTE
    assert trace.status_reason == "No candidate route available"
