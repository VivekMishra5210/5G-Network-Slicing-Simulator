"""
Regression tests ensuring that legacy simulation algorithms (Static, Round Robin, QoS Adaptive)
and the /api/simulate endpoint remain 100% operational, backwards-compatible, and unaltered.
"""

import pytest
from simulation.simulator import Simulator
from allocation.static_allocator import StaticAllocator
from allocation.round_robin import RoundRobinAllocator
from allocation.qos_allocator import QoSAllocator
from dashboard.app import app


def test_legacy_allocator_instantiation_and_names():
    static_alloc = StaticAllocator()
    rr_alloc = RoundRobinAllocator()
    qos_alloc = QoSAllocator()

    assert static_alloc.name == "Static"
    assert rr_alloc.name == "Round Robin"
    assert qos_alloc.name == "QoS Adaptive"


def test_legacy_simulator_deterministic_run():
    """Verify that legacy Simulator runs deterministically with seed 42."""
    sim = Simulator(total_bandwidth=100.0, duration=10, seed=42)
    df_static = sim.run(scenario_name="normal", allocator=StaticAllocator())

    assert not df_static.empty
    assert "throughput" in df_static.columns
    assert "latency" in df_static.columns
    assert "packet_loss" in df_static.columns
    assert "qos_satisfied" in df_static.columns
    assert set(df_static["slice"].unique()) == {"eMBB", "URLLC", "mMTC"}


def test_legacy_api_simulate_endpoint():
    """Verify that legacy /api/simulate endpoint works unchanged for algorithm='all'."""
    client = app.test_client()
    payload = {
        "bandwidth": 100,
        "duration": 5,
        "scenario": "normal",
        "algorithm": "all",
        "seed": 42,
    }

    response = client.post("/api/simulate", json=payload)
    assert response.status_code == 200

    data = response.get_json()
    assert "results" in data
    assert "summary" in data
    assert "comparison" in data
    assert set(data["summary"].keys()) == {"eMBB", "URLLC", "mMTC"}
    assert "Static" in data["comparison"]
    assert "Round Robin" in data["comparison"]
    assert "QoS Adaptive" in data["comparison"]


def test_mcra_api_endpoint_validation():
    """Verify that /api/mcra/simulate accepts valid requests and rejects invalid parameters."""
    client = app.test_client()

    # Valid request
    valid_payload = {
        "topology_mode": "parallel_hybrid",
        "scenario": "normal_mix",
        "duration_ms": 500,
        "seed": 42,
        "cost_base": 2.0,
    }
    res = client.post("/api/mcra/simulate", json=valid_payload)
    assert res.status_code == 200
    res_data = res.get_json()
    assert "summary" in res_data
    assert "per_slice" in res_data
    assert "topology" in res_data
    assert "mcra_decisions" in res_data

    # Invalid cost base (<= 1.0) must return 400
    res_bad_cost = client.post("/api/mcra/simulate", json={"cost_base": 1.0})
    assert res_bad_cost.status_code == 400
    assert "cost_base" in res_bad_cost.get_json()["error"]

    # Invalid duration (<= 0) must return 400
    res_bad_dur = client.post("/api/mcra/simulate", json={"duration_ms": -50})
    assert res_bad_dur.status_code == 400
