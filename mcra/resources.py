"""
Atomic resource ledger for communication links and compute nodes.
Guarantees invariant checks, prevents overbooking, and eliminates double-release bugs.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from mcra.models import ResourceType


class ResourceExhaustedError(Exception):
    """Raised when an atomic reservation violates resource capacity constraints."""
    pass


class InvalidReleaseError(Exception):
    """Raised when attempting an illegal or duplicate release."""
    pass


@dataclass
class ResourceEntry:
    resource_id: str
    resource_type: ResourceType
    total_capacity: float
    current_used: float = 0.0
    min_unit: float = 1.0
    # History for time-weighted utilization: list of (time_ms, used_val)
    history: List[Tuple[float, float]] = field(default_factory=list)

    @property
    def remaining(self) -> float:
        return max(0.0, self.total_capacity - self.current_used)


class ResourceLedger:
    """
    Single source of truth for resource capacity, reservation, and release.
    Guarantees atomic multi-resource allocation and idempotent release.
    """

    def __init__(self):
        self.resources: Dict[str, ResourceEntry] = {}
        # Tracks active reservations: reservation_id -> dict[resource_id, amount]
        self.active_reservations: Dict[str, Dict[str, float]] = {}
        # Set of released reservation IDs to prevent double-release
        self.released_reservations: set[str] = set()

    def register_resource(
        self,
        resource_id: str,
        total_capacity: float,
        resource_type: ResourceType,
        min_unit: float = 1.0,
    ) -> None:
        """Register a new resource node or link in the ledger."""
        if total_capacity <= 0:
            raise ValueError(f"Total capacity for {resource_id} must be positive, got {total_capacity}")
        self.resources[resource_id] = ResourceEntry(
            resource_id=resource_id,
            resource_type=resource_type,
            total_capacity=float(total_capacity),
            current_used=0.0,
            min_unit=float(min_unit),
            history=[(0.0, 0.0)],
        )

    def get_capacity(self, resource_id: str) -> float:
        return self.resources[resource_id].total_capacity

    def get_used(self, resource_id: str) -> float:
        return self.resources[resource_id].current_used

    def get_remaining(self, resource_id: str) -> float:
        return self.resources[resource_id].remaining

    def get_resource_type(self, resource_id: str) -> ResourceType:
        return self.resources[resource_id].resource_type

    def check_availability(self, plan: Dict[str, float]) -> bool:
        """Verify whether all resources in the tentative plan are available."""
        for res_id, amount in plan.items():
            if res_id not in self.resources:
                return False
            if amount < 0:
                return False
            if self.resources[res_id].remaining < amount - 1e-9:
                return False
        return True

    def reserve_atomic(
        self,
        reservation_id: str,
        allocations: Dict[str, float],
        current_time_ms: float = 0.0,
    ) -> bool:
        """
        Atomically reserve multiple resources.
        If any resource cannot fulfill the requested amount, completely rolls back
        and returns False without modifying the ledger state.
        """
        if reservation_id in self.active_reservations:
            raise ValueError(f"Reservation ID {reservation_id} already exists.")

        # Pre-check all resources
        for res_id, amount in allocations.items():
            if amount <= 0:
                continue
            if res_id not in self.resources:
                return False
            entry = self.resources[res_id]
            if entry.remaining < amount - 1e-9:
                return False

        # Apply atomically
        committed = {}
        try:
            for res_id, amount in allocations.items():
                if amount <= 0:
                    continue
                entry = self.resources[res_id]
                entry.current_used += amount
                entry.history.append((current_time_ms, entry.current_used))
                committed[res_id] = amount
                # Enforce invariant
                assert entry.current_used <= entry.total_capacity + 1e-7, (
                    f"Invariant violated on {res_id}: used {entry.current_used} > cap {entry.total_capacity}"
                )

            self.active_reservations[reservation_id] = committed
            return True
        except Exception:
            # Rollback if unexpected assertion
            for res_id, amount in committed.items():
                self.resources[res_id].current_used -= amount
            raise

    def release(self, reservation_id: str, current_time_ms: float = 0.0) -> bool:
        """
        Release all resources held by reservation_id.
        Guarantees single-release: returns True on first release, False if already released or unknown.
        """
        if reservation_id in self.released_reservations:
            # Already released, idempotent safeguard
            return False

        if reservation_id not in self.active_reservations:
            return False

        allocated_dict = self.active_reservations.pop(reservation_id)
        for res_id, amount in allocated_dict.items():
            if res_id in self.resources:
                entry = self.resources[res_id]
                entry.current_used = max(0.0, entry.current_used - amount)
                entry.history.append((current_time_ms, entry.current_used))

        self.released_reservations.add(reservation_id)
        return True

    def calculate_time_weighted_utilization(
        self, resource_id: str, total_duration_ms: float
    ) -> float:
        """
        Compute the exact time-weighted utilization (%) over [0, total_duration_ms].
        Integral of used(t) / (capacity * duration).
        """
        if resource_id not in self.resources or total_duration_ms <= 0:
            return 0.0

        entry = self.resources[resource_id]
        if not entry.history:
            return 0.0

        capacity = entry.total_capacity
        integral = 0.0
        points = list(entry.history)
        if points[-1][0] < total_duration_ms:
            points.append((total_duration_ms, points[-1][1]))

        for i in range(len(points) - 1):
            t_start, u_val = points[i]
            t_end, _ = points[i + 1]
            t_span = max(0.0, min(total_duration_ms, t_end) - t_start)
            integral += u_val * t_span

        avg_used = integral / total_duration_ms
        return min(100.0, (avg_used / capacity) * 100.0)

    def get_snapshot(self) -> Dict[str, Dict[str, float]]:
        """Return current utilization snapshot of all resources."""
        snapshot = {}
        for res_id, entry in self.resources.items():
            snapshot[res_id] = {
                "capacity": entry.total_capacity,
                "used": round(entry.current_used, 3),
                "remaining": round(entry.remaining, 3),
                "utilization_pct": round((entry.current_used / entry.total_capacity) * 100.0, 2),
                "resource_type": entry.resource_type.value,
            }
        return snapshot
