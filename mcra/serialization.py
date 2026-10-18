"""
JSON-safe serialization and CSV row formatting for MCRA simulation outputs.
"""

import math
from typing import Any, Dict, List


def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively sanitize floating point numbers to ensure JSON compliance.
    Converts NaN, Infinity, and -Infinity to safe representations or None.
    """
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return round(obj, 4)
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(x) for x in obj]
    elif hasattr(obj, "to_dict"):
        return sanitize_for_json(obj.to_dict())
    return obj


def format_csv_request_rows(requests: List[Any]) -> List[Dict[str, Any]]:
    """Format request records for CSV export."""
    rows = []
    for r in requests:
        rows.append({
            "request_id": r.request_id,
            "tenant_id": r.tenant_id,
            "slice_type": r.slice_type.value,
            "arrival_time_ms": round(r.arrival_time_ms, 2),
            "payload_bits": round(r.payload_bits, 1),
            "compute_demand": round(r.compute_demand, 2),
            "deadline_ms": round(r.deadline_ms, 2),
            "route_candidate": r.route_candidate or "none",
            "status": r.status.value,
            "status_reason": r.status_reason,
            "predicted_delay_ms": round(r.predicted_delay_ms, 2),
            "actual_e2e_delay_ms": round(r.actual_e2e_delay_ms, 2),
            "completion_time_ms": round(r.completion_time_ms, 2),
            "deadline_met": bool(r.actual_e2e_delay_ms <= r.deadline_ms and r.status.value == "COMPLETED"),
        })
    return rows
