"""
Unit tests for atomic resource ledger, capacity checks, and single-release invariants.
"""

import pytest
from mcra.models import ResourceType
from mcra.resources import ResourceLedger


def test_ledger_registration_and_initial_state():
    ledger = ResourceLedger()
    ledger.register_resource("link_access", 100.0, ResourceType.COMMUNICATION)
    ledger.register_resource("edge_compute", 50.0, ResourceType.COMPUTATION)

    assert ledger.get_capacity("link_access") == 100.0
    assert ledger.get_used("link_access") == 0.0
    assert ledger.get_remaining("link_access") == 100.0

    assert ledger.get_capacity("edge_compute") == 50.0
    assert ledger.get_remaining("edge_compute") == 50.0


def test_atomic_reservation_success():
    ledger = ResourceLedger()
    ledger.register_resource("link_access", 100.0, ResourceType.COMMUNICATION)
    ledger.register_resource("edge_compute", 50.0, ResourceType.COMPUTATION)

    plan = {"link_access": 30.0, "edge_compute": 20.0}
    success = ledger.reserve_atomic("req_1", plan, current_time_ms=5.0)

    assert success is True
    assert ledger.get_used("link_access") == 30.0
    assert ledger.get_remaining("link_access") == 70.0
    assert ledger.get_used("edge_compute") == 20.0
    assert ledger.get_remaining("edge_compute") == 30.0


def test_atomic_reservation_rollback_on_partial_failure():
    """
    If one resource has sufficient capacity but another is insufficient,
    neither resource must be modified (strict atomic all-or-nothing).
    """
    ledger = ResourceLedger()
    ledger.register_resource("link_access", 100.0, ResourceType.COMMUNICATION)
    ledger.register_resource("edge_compute", 20.0, ResourceType.COMPUTATION)

    # link_access has enough (50 <= 100), but edge_compute exceeds (30 > 20)
    overbooking_plan = {"link_access": 50.0, "edge_compute": 30.0}
    success = ledger.reserve_atomic("req_fail", overbooking_plan, current_time_ms=10.0)

    assert success is False
    # Verify link_access was untouched!
    assert ledger.get_used("link_access") == 0.0
    assert ledger.get_remaining("link_access") == 100.0
    assert ledger.get_used("edge_compute") == 0.0


def test_single_release_and_idempotence():
    ledger = ResourceLedger()
    ledger.register_resource("link_access", 100.0, ResourceType.COMMUNICATION)

    ledger.reserve_atomic("req_1", {"link_access": 40.0}, current_time_ms=0.0)
    assert ledger.get_used("link_access") == 40.0

    # First release succeeds
    released_1 = ledger.release("req_1", current_time_ms=15.0)
    assert released_1 is True
    assert ledger.get_used("link_access") == 0.0
    assert ledger.get_remaining("link_access") == 100.0

    # Second release of same reservation must return False (no double release)
    released_2 = ledger.release("req_1", current_time_ms=20.0)
    assert released_2 is False
    assert ledger.get_used("link_access") == 0.0


def test_time_weighted_utilization():
    ledger = ResourceLedger()
    ledger.register_resource("link_access", 100.0, ResourceType.COMMUNICATION)

    # 0 to 10 ms: 0 used
    # 10 to 30 ms: 50 used (duration 20 ms) -> 50 * 20 = 1000
    # 30 to 50 ms: 100 used (duration 20 ms) -> 100 * 20 = 2000
    # Total integral = 3000 over 50 ms. Average used = 3000 / 50 = 60.
    # Utilization = 60 / 100 = 60.0%
    ledger.reserve_atomic("r1", {"link_access": 50.0}, current_time_ms=10.0)
    ledger.reserve_atomic("r2", {"link_access": 50.0}, current_time_ms=30.0)

    util = ledger.calculate_time_weighted_utilization("link_access", total_duration_ms=50.0)
    assert pytest.approx(util, rel=1e-3) == 60.0
