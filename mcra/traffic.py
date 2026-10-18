"""
Reproducible traffic generation module for MCRA simulation.
Generates discrete service requests with payload sizes, compute demands, deadlines, and multi-tenant profiles.
Includes TraceReplayer for real commercial 5G NR traces and standard NS-3 ASCII trace playback.
"""

import csv
import os
import re
from typing import List, Dict, Optional
import numpy as np
from mcra.models import ServiceRequest, Packet, SliceType, QoSProfile


# Standard QoS Profiles for the 3 Slices
MCRA_QOS_PROFILES = {
    SliceType.EMBB: QoSProfile(
        slice_type=SliceType.EMBB,
        deadline_ms=80.0,
        max_loss_pct=5.0,
        min_bw_mbps=5.0,
        min_compute_units=2.0,
    ),
    SliceType.URLLC: QoSProfile(
        slice_type=SliceType.URLLC,
        deadline_ms=8.0,
        max_loss_pct=1.0,
        min_bw_mbps=10.0,
        min_compute_units=5.0,
    ),
    SliceType.MMTC: QoSProfile(
        slice_type=SliceType.MMTC,
        deadline_ms=150.0,
        max_loss_pct=10.0,
        min_bw_mbps=1.0,
        min_compute_units=0.5,
    ),
}


class TraceReplayer:
    """
    Parses and replays real-world commercial 5G NR traces and NS-3 ASCII packet traces
    into deterministic ServiceRequest sequences for research benchmarking.
    """

    @staticmethod
    def load_csv_trace(file_path: str, max_duration_ms: Optional[float] = None) -> List[ServiceRequest]:
        """Load service requests from a 5G NR CSV trace dataset."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Trace file not found: {file_path}")

        requests = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            req_idx = 0
            for row in reader:
                t_ms = float(row["timestamp_ms"])
                if max_duration_ms and t_ms > max_duration_ms:
                    continue
                req_idx += 1
                tenant_id = row.get("tenant_id", "tenant_1").strip()
                stype_str = row.get("slice_type", "URLLC").strip()
                stype = SliceType(stype_str) if stype_str in [s.value for s in SliceType] else SliceType.URLLC
                payload_bits = float(row.get("payload_bytes", 1000)) * 8.0
                compute_demand = float(row.get("compute_demand", 5.0))
                deadline_ms = float(row.get("deadline_ms", 20.0))

                req = ServiceRequest(
                    request_id=f"trace_{stype.value}_{req_idx:04d}",
                    tenant_id=tenant_id,
                    ue_id=f"ue_{tenant_id}_{req_idx}",
                    slice_type=stype,
                    arrival_time_ms=t_ms,
                    payload_bits=payload_bits,
                    compute_demand=compute_demand,
                    deadline_ms=deadline_ms,
                )
                requests.append(req)
        return requests

    @staticmethod
    def load_ns3_ascii_trace(
        file_path: str, slice_type: SliceType = SliceType.URLLC, max_duration_ms: Optional[float] = None
    ) -> List[ServiceRequest]:
        """Load packet arrivals from a standard NS-3 ASCII trace file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"NS-3 trace file not found: {file_path}")

        requests = []
        with open(file_path, "r", encoding="utf-8") as f:
            req_idx = 0
            for line in f:
                line = line.strip()
                if not line or not line.startswith("+"):
                    continue  # Only capture '+' enqueue events as packet arrivals

                tokens = line.split()
                if len(tokens) < 2:
                    continue
                try:
                    time_sec = float(tokens[1])
                    t_ms = time_sec * 1000.0
                except ValueError:
                    continue

                if max_duration_ms and t_ms > max_duration_ms:
                    continue

                # Extract length: <num>
                length_match = re.search(r"length:\s*(\d+)", line)
                payload_bytes = float(length_match.group(1)) if length_match else 512.0
                payload_bits = payload_bytes * 8.0

                req_idx += 1
                req = ServiceRequest(
                    request_id=f"ns3_req_{req_idx:04d}",
                    tenant_id="tenant_1" if req_idx % 2 == 1 else "tenant_2",
                    ue_id=f"ue_ns3_{req_idx}",
                    slice_type=slice_type,
                    arrival_time_ms=t_ms,
                    payload_bits=payload_bits,
                    compute_demand=3.0,
                    deadline_ms=8.0 if slice_type == SliceType.URLLC else 80.0,
                )
                requests.append(req)
        return requests

    @classmethod
    def load_combined_5g_nr_traces(cls, trace_dir: str, duration_ms: float = 1000.0) -> List[ServiceRequest]:
        """Combine eMBB, URLLC, and mMTC 5G NR trace files into one chronological request stream."""
        embb_file = os.path.join(trace_dir, "5g_nr_embb_video.csv")
        urllc_file = os.path.join(trace_dir, "5g_nr_urllc_telemetry.csv")
        mmtc_file = os.path.join(trace_dir, "5g_nr_mmtc_smartgrid.csv")

        all_reqs = []
        if os.path.exists(embb_file):
            all_reqs.extend(cls.load_csv_trace(embb_file, max_duration_ms=duration_ms))
        if os.path.exists(urllc_file):
            all_reqs.extend(cls.load_csv_trace(urllc_file, max_duration_ms=duration_ms))
        if os.path.exists(mmtc_file):
            all_reqs.extend(cls.load_csv_trace(mmtc_file, max_duration_ms=duration_ms))

        # Sort all requests chronologically by arrival_time_ms
        all_reqs.sort(key=lambda r: r.arrival_time_ms)
        return all_reqs


class MCRATrafficGenerator:
    """
    Deterministic traffic generator producing ServiceRequests across simulation time.
    Supports synthetic scenarios and real commercial 5G NR / NS-3 trace playback.
    """

    def __init__(self, seed: int = 42, max_packet_size_bits: float = 12000.0):
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        self.max_packet_size_bits = max_packet_size_bits

    def packetize_request(self, request: ServiceRequest) -> List[Packet]:
        """Split a request into packets if payload exceeds max_packet_size_bits."""
        total_bits = request.payload_bits
        if total_bits <= self.max_packet_size_bits:
            pkt = Packet(
                packet_id=f"{request.request_id}_pkt_0",
                parent_request_id=request.request_id,
                sequence_number=0,
                total_packets=1,
                payload_bits=total_bits,
                creation_time_ms=request.arrival_time_ms,
            )
            return [pkt]

        packets = []
        num_pkts = int(np.ceil(total_bits / self.max_packet_size_bits))
        remaining = total_bits

        for seq in range(num_pkts):
            pkt_bits = min(self.max_packet_size_bits, remaining)
            pkt = Packet(
                packet_id=f"{request.request_id}_pkt_{seq}",
                parent_request_id=request.request_id,
                sequence_number=seq,
                total_packets=num_pkts,
                payload_bits=pkt_bits,
                creation_time_ms=request.arrival_time_ms,
            )
            packets.append(pkt)
            remaining -= pkt_bits

        return packets

    def generate_trace(
        self,
        scenario: str = "normal_mix",
        duration_ms: float = 1000.0,
        num_tenants: int = 2,
        arrival_rate_scale: float = 1.0,
    ) -> List[ServiceRequest]:
        """
        Generate a list of requests sorted chronologically by arrival_time_ms.
        Supports synthetic generation and real-world 5G NR / NS-3 trace playback.
        """
        # 1. Check for real-world Trace Playback modes
        normalized_scenario = scenario.lower().replace("-", "_").strip()

        if normalized_scenario in ["trace_playback", "5g_nr_trace_playback", "commercial_trace"]:
            trace_dir = os.path.join(os.path.dirname(__file__), "..", "data", "traces")
            trace_reqs = TraceReplayer.load_combined_5g_nr_traces(trace_dir=trace_dir, duration_ms=duration_ms)
            for r in trace_reqs:
                r.packets = self.packetize_request(r)
            return trace_reqs

        elif normalized_scenario in ["ns3_trace", "ns3_playback"]:
            trace_file = os.path.join(os.path.dirname(__file__), "..", "data", "traces", "ns3_ascii_trace_sample.txt")
            trace_reqs = TraceReplayer.load_ns3_ascii_trace(trace_file, max_duration_ms=duration_ms)
            for r in trace_reqs:
                r.packets = self.packetize_request(r)
            return trace_reqs

        # 2. Synthetic Scenario Generation Pipeline
        requests: List[ServiceRequest] = []
        req_counter = 0

        scenarios_cfg = {
            "normal_mix": {
                SliceType.EMBB: {"rate": 2.5 * arrival_rate_scale, "payload": (40000, 80000), "compute": (5, 15), "deadline": (60, 90)},
                SliceType.URLLC: {"rate": 2.0 * arrival_rate_scale, "payload": (2000, 6000), "compute": (2, 6), "deadline": (5, 8)},
                SliceType.MMTC: {"rate": 3.0 * arrival_rate_scale, "payload": (500, 1500), "compute": (0.5, 2), "deadline": (120, 180)},
            },
            "embb_surge": {
                SliceType.EMBB: {"rate": 7.0 * arrival_rate_scale, "payload": (60000, 120000), "compute": (10, 25), "deadline": (60, 90)},
                SliceType.URLLC: {"rate": 1.5 * arrival_rate_scale, "payload": (2000, 6000), "compute": (2, 6), "deadline": (5, 8)},
                SliceType.MMTC: {"rate": 2.0 * arrival_rate_scale, "payload": (500, 1500), "compute": (0.5, 2), "deadline": (120, 180)},
            },
            "urllc_emergency": {
                SliceType.EMBB: {"rate": 2.0 * arrival_rate_scale, "payload": (30000, 60000), "compute": (5, 12), "deadline": (60, 90)},
                SliceType.URLLC: {"rate": 8.0 * arrival_rate_scale, "payload": (3000, 8000), "compute": (3, 8), "deadline": (4, 7)},
                SliceType.MMTC: {"rate": 2.0 * arrival_rate_scale, "payload": (500, 1500), "compute": (0.5, 2), "deadline": (120, 180)},
            },
            "mmtc_surge": {
                SliceType.EMBB: {"rate": 1.5 * arrival_rate_scale, "payload": (30000, 60000), "compute": (5, 12), "deadline": (60, 90)},
                SliceType.URLLC: {"rate": 1.5 * arrival_rate_scale, "payload": (2000, 5000), "compute": (2, 5), "deadline": (5, 8)},
                SliceType.MMTC: {"rate": 12.0 * arrival_rate_scale, "payload": (800, 2000), "compute": (1, 3), "deadline": (100, 160)},
            },
            "edge_overload": {
                SliceType.EMBB: {"rate": 4.0 * arrival_rate_scale, "payload": (40000, 80000), "compute": (20, 40), "deadline": (50, 80)},
                SliceType.URLLC: {"rate": 4.0 * arrival_rate_scale, "payload": (3000, 8000), "compute": (10, 20), "deadline": (5, 9)},
                SliceType.MMTC: {"rate": 4.0 * arrival_rate_scale, "payload": (500, 2000), "compute": (2, 5), "deadline": (120, 180)},
            },
            "backhaul_congestion": {
                SliceType.EMBB: {"rate": 5.0 * arrival_rate_scale, "payload": (70000, 150000), "compute": (5, 15), "deadline": (60, 100)},
                SliceType.URLLC: {"rate": 3.0 * arrival_rate_scale, "payload": (2000, 6000), "compute": (2, 6), "deadline": (5, 8)},
                SliceType.MMTC: {"rate": 3.0 * arrival_rate_scale, "payload": (500, 1500), "compute": (0.5, 2), "deadline": (120, 180)},
            },
            "mixed_peak": {
                SliceType.EMBB: {"rate": 5.0 * arrival_rate_scale, "payload": (50000, 100000), "compute": (10, 20), "deadline": (50, 80)},
                SliceType.URLLC: {"rate": 5.0 * arrival_rate_scale, "payload": (3000, 7000), "compute": (3, 7), "deadline": (5, 8)},
                SliceType.MMTC: {"rate": 8.0 * arrival_rate_scale, "payload": (600, 1800), "compute": (1, 3), "deadline": (100, 160)},
            },
            "dynamic_day": {"dynamic": True},
        }

        cfg = scenarios_cfg.get(normalized_scenario, scenarios_cfg["normal_mix"])
        tenants = [f"tenant_{t+1}" for t in range(num_tenants)]

        step_interval_ms = 50.0
        intervals = int(duration_ms / step_interval_ms)

        for step in range(intervals):
            current_t = step * step_interval_ms

            active_cfg = cfg
            if normalized_scenario == "dynamic_day":
                if current_t < 0.25 * duration_ms:
                    active_cfg = scenarios_cfg["normal_mix"]
                elif current_t < 0.50 * duration_ms:
                    active_cfg = scenarios_cfg["embb_surge"]
                elif current_t < 0.75 * duration_ms:
                    active_cfg = scenarios_cfg["urllc_emergency"]
                else:
                    active_cfg = scenarios_cfg["normal_mix"]

            for slice_type in [SliceType.EMBB, SliceType.URLLC, SliceType.MMTC]:
                slice_spec = active_cfg[slice_type]
                expected_arrivals = slice_spec["rate"] * (step_interval_ms / 100.0)
                num_arrivals = self.rng.poisson(lam=max(0.01, expected_arrivals))

                for _ in range(num_arrivals):
                    req_counter += 1
                    arrival_offset = self.rng.uniform(0, step_interval_ms)
                    arr_time = min(duration_ms, current_t + arrival_offset)

                    tenant = tenants[self.rng.choice(len(tenants))]
                    p_min, p_max = slice_spec["payload"]
                    c_min, c_max = slice_spec["compute"]
                    d_min, d_max = slice_spec["deadline"]

                    payload = float(self.rng.uniform(p_min, p_max))
                    compute = float(self.rng.uniform(c_min, c_max))
                    deadline = float(self.rng.uniform(d_min, d_max))

                    req = ServiceRequest(
                        request_id=f"req_{req_counter:04d}",
                        tenant_id=tenant,
                        ue_id=f"ue_{tenant}_{slice_type.value}_{req_counter}",
                        slice_type=slice_type,
                        arrival_time_ms=arr_time,
                        payload_bits=payload,
                        compute_demand=compute,
                        deadline_ms=deadline,
                    )
                    req.packets = self.packetize_request(req)
                    requests.append(req)

        # Sort all requests chronologically by arrival time
        requests.sort(key=lambda r: r.arrival_time_ms)
        return requests
