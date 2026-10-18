"""
Unit tests for 5G NR commercial trace playback and NS-3 ASCII trace replay engine.
"""

import os
import pytest
from mcra.models import SliceType
from mcra.traffic import TraceReplayer
from mcra.simulation import MCRASimulator


def test_load_csv_trace():
    trace_file = os.path.join(os.path.dirname(__file__), "..", "data", "traces", "5g_nr_urllc_telemetry.csv")
    requests = TraceReplayer.load_csv_trace(trace_file, max_duration_ms=500.0)

    assert len(requests) > 0
    for req in requests:
        assert req.slice_type == SliceType.URLLC
        assert req.arrival_time_ms <= 500.0
        assert req.payload_bits > 0
        assert req.compute_demand > 0
        assert req.deadline_ms <= 10.0


def test_load_ns3_ascii_trace():
    trace_file = os.path.join(os.path.dirname(__file__), "..", "data", "traces", "ns3_ascii_trace_sample.txt")
    requests = TraceReplayer.load_ns3_ascii_trace(trace_file, slice_type=SliceType.URLLC, max_duration_ms=500.0)

    assert len(requests) > 0
    # First line in trace is + 0.010500 -> 10.5 ms
    assert pytest.approx(requests[0].arrival_time_ms, rel=1e-3) == 10.5
    # Length was 512 bytes = 4096 bits
    assert requests[0].payload_bits == 512.0 * 8.0


def test_load_combined_5g_nr_traces_chronological_order():
    trace_dir = os.path.join(os.path.dirname(__file__), "..", "data", "traces")
    requests = TraceReplayer.load_combined_5g_nr_traces(trace_dir, duration_ms=1000.0)

    assert len(requests) >= 50
    # Must be strictly ordered chronologically
    for i in range(len(requests) - 1):
        assert requests[i].arrival_time_ms <= requests[i + 1].arrival_time_ms


def test_simulation_with_trace_playback_scenario():
    """Verify that MCRASimulator executes end-to-end using commercial 5G NR trace playback."""
    sim = MCRASimulator(seed=42)
    results = sim.run(scenario="trace_playback", duration_ms=1000.0)

    assert "summary" in results
    assert results["summary"]["total_offered_requests"] > 0
    assert results["summary"]["total_admitted_requests"] > 0
    assert results["summary"]["total_completed_requests"] > 0
    assert results["summary"]["delivered_throughput_mbps"] >= 0.0
    assert set(results["per_slice"].keys()) == {"eMBB", "URLLC", "mMTC"}


def test_simulation_with_ns3_trace_scenario():
    """Verify that MCRASimulator executes end-to-end using NS-3 trace playback."""
    sim = MCRASimulator(seed=42)
    results = sim.run(scenario="ns3_trace", duration_ms=500.0)

    assert "summary" in results
    assert results["summary"]["total_offered_requests"] > 0
    assert results["summary"]["total_completed_requests"] > 0
