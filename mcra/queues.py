"""
Queues for communication links and compute nodes.
Supports FIFO and priority disciplines with finite buffer capacities and drop accounting.
"""

from collections import deque
from dataclasses import dataclass
from typing import Optional, List, Tuple
from mcra.models import Packet


@dataclass
class QueuedItem:
    packet: Packet
    enqueue_time_ms: float


class PacketQueue:
    """
    Finite-buffer queue tracking enqueue, dequeue, wait times, and overflow drops.
    """

    def __init__(self, queue_id: str, capacity_packets: int = 100):
        self.queue_id = queue_id
        self.capacity_packets = capacity_packets
        self._queue: deque[QueuedItem] = deque()
        self.total_enqueued: int = 0
        self.total_dequeued: int = 0
        self.total_dropped: int = 0
        self.waiting_times_ms: List[float] = []

    @property
    def size(self) -> int:
        return len(self._queue)

    @property
    def is_empty(self) -> bool:
        return len(self._queue) == 0

    @property
    def is_full(self) -> bool:
        return len(self._queue) >= self.capacity_packets

    def enqueue(self, packet: Packet, current_time_ms: float) -> bool:
        """
        Attempt to enqueue a packet.
        Returns True if enqueued, False if dropped due to buffer overflow.
        """
        if self.is_full:
            self.total_dropped += 1
            return False

        self._queue.append(QueuedItem(packet=packet, enqueue_time_ms=current_time_ms))
        self.total_enqueued += 1
        return True

    def dequeue(self, current_time_ms: float) -> Optional[Tuple[Packet, float]]:
        """
        Dequeue next packet and record wait time.
        Returns (packet, wait_time_ms) or None if empty.
        """
        if not self._queue:
            return None

        item = self._queue.popleft()
        wait_time_ms = max(0.0, current_time_ms - item.enqueue_time_ms)
        self.waiting_times_ms.append(wait_time_ms)
        self.total_dequeued += 1
        return item.packet, wait_time_ms

    def peek(self) -> Optional[Packet]:
        if not self._queue:
            return None
        return self._queue[0].packet

    def average_wait_time_ms(self) -> float:
        if not self.waiting_times_ms:
            return 0.0
        return sum(self.waiting_times_ms) / len(self.waiting_times_ms)
