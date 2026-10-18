"""
Unit tests for fixed seed reproducibility of traffic traces and simulations.
"""

import pytest
from mcra.traffic import MCRATrafficGenerator


def test_fixed_seed_reproducible_traces():
    gen1 = MCRATrafficGenerator(seed=42)
    trace1 = gen1.generate_trace(scenario="normal_mix", duration_ms=500.0)

    gen2 = MCRATrafficGenerator(seed=42)
    trace2 = gen2.generate_trace(scenario="normal_mix", duration_ms=500.0)

    assert len(trace1) == len(trace2)
    for r1, r2 in zip(trace1, trace2):
        assert r1.request_id == r2.request_id
        assert r1.arrival_time_ms == r2.arrival_time_ms
        assert r1.payload_bits == r2.payload_bits
        assert r1.compute_demand == r2.compute_demand
        assert r1.deadline_ms == r2.deadline_ms


def test_different_seeds_produce_different_traces():
    gen1 = MCRATrafficGenerator(seed=42)
    trace1 = gen1.generate_trace(scenario="normal_mix", duration_ms=500.0)

    gen2 = MCRATrafficGenerator(seed=999)
    trace2 = gen2.generate_trace(scenario="normal_mix", duration_ms=500.0)

    # Payloads and arrival times should differ
    diff_count = sum(1 for r1, r2 in zip(trace1, trace2) if r1.arrival_time_ms != r2.arrival_time_ms)
    assert diff_count > 0
