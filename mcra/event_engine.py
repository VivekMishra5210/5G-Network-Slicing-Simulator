"""
Deterministic discrete-event priority queue engine for MCRA simulation.
Orders events strictly by (time_ms, stable_sequence) to guarantee reproducible execution.
"""

import heapq
from typing import Optional, List, Dict, Any
from mcra.models import SimulationEvent, EventType


class EventEngine:
    """
    Discrete-event priority queue.
    Advances the simulation clock to the next event time without arbitrary wall-clock sleep.
    """

    def __init__(self):
        # Priority queue storing tuples: (time_ms, sequence, SimulationEvent)
        self._heap: List[tuple[float, int, SimulationEvent]] = []
        self._sequence_counter: int = 0
        self.current_time_ms: float = 0.0
        self.event_log: List[SimulationEvent] = []

    def schedule(
        self,
        time_ms: float,
        event_type: EventType,
        request_id: str,
        packet_id: Optional[str] = None,
        node_or_link_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SimulationEvent:
        """Schedule a new event at time_ms."""
        if time_ms < self.current_time_ms - 1e-9:
            raise ValueError(
                f"Cannot schedule event in the past: time_ms={time_ms} < current={self.current_time_ms}"
            )

        self._sequence_counter += 1
        event = SimulationEvent(
            time_ms=float(time_ms),
            sequence=self._sequence_counter,
            event_type=event_type,
            request_id=request_id,
            packet_id=packet_id,
            node_or_link_id=node_or_link_id,
            metadata=metadata or {},
        )
        heapq.heappush(self._heap, (event.time_ms, event.sequence, event))
        return event

    def has_events(self) -> bool:
        return len(self._heap) > 0

    def peek_next_time(self) -> Optional[float]:
        if not self._heap:
            return None
        return self._heap[0][0]

    def pop_next(self) -> Optional[SimulationEvent]:
        """Pop and return the earliest scheduled event, advancing simulation clock."""
        if not self._heap:
            return None

        time_ms, _, event = heapq.heappop(self._heap)
        assert time_ms >= self.current_time_ms - 1e-9, "Clock monotonicity violated!"
        self.current_time_ms = time_ms
        self.event_log.append(event)
        return event

    def count_pending(self) -> int:
        return len(self._heap)

    def clear(self) -> None:
        self._heap.clear()
        self._sequence_counter = 0
        self.current_time_ms = 0.0
        self.event_log.clear()
