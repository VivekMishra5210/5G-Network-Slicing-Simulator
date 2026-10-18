"""
Metrics calculation module for the MCRA simulation engine.
Computes precise request-level, packet-level, time-weighted resource, and QoS SLA metrics.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from mcra.models import ServiceRequest, Packet, RequestStatus, SliceType
from mcra.resources import ResourceLedger


class MCRAMetricsEngine:
    """
    Computes rigorous metrics from simulation event logs and completed requests.
    Prevents synthetic approximations: all figures derive directly from actual events.
    """

    @staticmethod
    def compute_all_metrics(
        requests: List[ServiceRequest],
        all_packets: List[Packet],
        ledger: ResourceLedger,
        total_duration_ms: float,
        iterations_log: List[int],
    ) -> Dict[str, Any]:
        offered = len(requests)
        admitted = [r for r in requests if r.status in [RequestStatus.ADMITTED, RequestStatus.COMPLETED]]
        blocked = [r for r in requests if r.status.value.startswith("BLOCKED")]
        completed = [r for r in requests if r.status == RequestStatus.COMPLETED]

        num_offered = offered
        num_admitted = len(admitted)
        num_blocked = len(blocked)
        num_completed = len(completed)

        blocking_prob = (num_blocked / num_offered) if num_offered > 0 else 0.0
        completion_ratio = (num_completed / num_admitted) if num_admitted > 0 else 0.0

        # Latency statistics on completed requests
        e2e_delays = [r.actual_e2e_delay_ms for r in completed if r.actual_e2e_delay_ms > 0]
        mean_delay = float(np.mean(e2e_delays)) if e2e_delays else 0.0
        median_delay = float(np.median(e2e_delays)) if e2e_delays else 0.0
        p95_delay = float(np.percentile(e2e_delays, 95)) if e2e_delays else 0.0
        p99_delay = float(np.percentile(e2e_delays, 99)) if e2e_delays else 0.0

        # Deadline success: completed requests with actual delay <= deadline
        deadline_met = [r for r in completed if r.actual_e2e_delay_ms <= r.deadline_ms]
        deadline_success_ratio = (len(deadline_met) / num_completed) if num_completed > 0 else 0.0

        # Packet level statistics
        total_packets = len(all_packets)
        delivered_packets = [p for p in all_packets if p.delivered]
        num_delivered = len(delivered_packets)
        pdr = (num_delivered / total_packets) if total_packets > 0 else 0.0

        # Delivered throughput in Mbps = total delivered payload bits / (duration_ms / 1000) / 1e6
        total_delivered_bits = sum(p.payload_bits for p in delivered_packets)
        duration_sec = total_duration_ms / 1000.0
        throughput_mbps = (total_delivered_bits / duration_sec / 1e6) if duration_sec > 0 else 0.0

        # Per-slice metrics
        per_slice: Dict[str, Any] = {}
        for stype in [SliceType.EMBB, SliceType.URLLC, SliceType.MMTC]:
            slice_reqs = [r for r in requests if r.slice_type == stype]
            slice_completed = [r for r in slice_reqs if r.status == RequestStatus.COMPLETED]
            slice_delays = [r.actual_e2e_delay_ms for r in slice_completed if r.actual_e2e_delay_ms > 0]
            slice_qos_met = [r for r in slice_completed if r.actual_e2e_delay_ms <= r.deadline_ms]

            slice_offered = len(slice_reqs)
            slice_admitted = len([r for r in slice_reqs if r.status in [RequestStatus.ADMITTED, RequestStatus.COMPLETED]])
            slice_blocked = len([r for r in slice_reqs if r.status.value.startswith("BLOCKED")])

            per_slice[stype.value] = {
                "offered_requests": slice_offered,
                "admitted_requests": slice_admitted,
                "blocked_requests": slice_blocked,
                "completed_requests": len(slice_completed),
                "blocking_probability": round((slice_blocked / slice_offered), 4) if slice_offered > 0 else 0.0,
                "mean_e2e_delay_ms": round(float(np.mean(slice_delays)), 2) if slice_delays else 0.0,
                "p95_delay_ms": round(float(np.percentile(slice_delays, 95)), 2) if slice_delays else 0.0,
                "qos_satisfaction_pct": round((len(slice_qos_met) / slice_offered) * 100.0, 2) if slice_offered > 0 else 0.0,
            }

        # Per-tenant metrics
        per_tenant: Dict[str, Any] = {}
        all_tenants = sorted(list({r.tenant_id for r in requests}))
        for t_id in all_tenants:
            t_reqs = [r for r in requests if r.tenant_id == t_id]
            t_admitted = len([r for r in t_reqs if r.status in [RequestStatus.ADMITTED, RequestStatus.COMPLETED]])
            t_blocked = len([r for r in t_reqs if r.status.value.startswith("BLOCKED")])
            t_completed = [r for r in t_reqs if r.status == RequestStatus.COMPLETED]
            t_qos_met = [r for r in t_completed if r.actual_e2e_delay_ms <= r.deadline_ms]

            per_tenant[t_id] = {
                "offered_requests": len(t_reqs),
                "admitted_requests": t_admitted,
                "blocked_requests": t_blocked,
                "completed_requests": len(t_completed),
                "blocking_probability": round((t_blocked / len(t_reqs)), 4) if t_reqs else 0.0,
                "qos_satisfaction_pct": round((len(t_qos_met) / len(t_reqs)) * 100.0, 2) if t_reqs else 0.0,
            }

        # Time-weighted resource utilization
        resource_utilization: Dict[str, float] = {}
        for res_id in ledger.resources.keys():
            util_pct = ledger.calculate_time_weighted_utilization(res_id, total_duration_ms)
            resource_utilization[res_id] = round(util_pct, 2)

        # MCRA algorithm diagnostics
        avg_iterations = float(np.mean(iterations_log)) if iterations_log else 0.0

        return {
            "summary": {
                "total_offered_requests": num_offered,
                "total_admitted_requests": num_admitted,
                "total_blocked_requests": num_blocked,
                "total_completed_requests": num_completed,
                "blocking_probability": round(blocking_prob, 4),
                "completion_ratio": round(completion_ratio, 4),
                "deadline_success_ratio": round(deadline_success_ratio, 4),
                "mean_e2e_delay_ms": round(mean_delay, 2),
                "median_e2e_delay_ms": round(median_delay, 2),
                "p95_delay_ms": round(p95_delay, 2),
                "p99_delay_ms": round(p99_delay, 2),
                "total_packets": total_packets,
                "delivered_packets": num_delivered,
                "packet_delivery_ratio": round(pdr, 4),
                "delivered_throughput_mbps": round(throughput_mbps, 3),
                "avg_mcra_iterations": round(avg_iterations, 2),
            },
            "per_slice": per_slice,
            "per_tenant": per_tenant,
            "resource_utilization": resource_utilization,
        }
