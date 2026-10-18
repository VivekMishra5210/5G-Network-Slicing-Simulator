"""
Unit tests for deterministic discrete-event engine and queue disciplines.
"""

import pytest
from mcra.models import EventType, Packet
from mcra.event_engine import EventEngine
from mcra.queues import PacketQueue


def test_event_engine_chronological_ordering():
    engine = EventEngine()
    engine.schedule(time_ms=10.0, event_type=EventType.REQUEST_ARRIVAL, request_id="r1")
    engine.schedule(time_ms=5.0, event_type=EventType.REQUEST_ARRIVAL, request_id="r2")
    engine.schedule(time_ms=15.0, event_type=EventType.REQUEST_ARRIVAL, request_id="r3")
    engine.schedule(time_ms=5.0, event_type=EventType.PACKET_DELIVERED, request_id="r2_sub")

    ev1 = engine.pop_next()
    assert ev1.time_ms == 5.0
    assert ev1.request_id == "r2"

    ev2 = engine.pop_next()
    assert ev2.time_ms == 5.0
    assert ev2.request_id == "r2_sub"

    ev3 = engine.pop_next()
    assert ev3.time_ms == 10.0
    assert ev3.request_id == "r1"

    ev4 = engine.pop_next()
    assert ev4.time_ms == 15.0
    assert ev4.request_id == "r3"

    assert not engine.has_events()


def test_packet_queue_finite_overflow_drops():
    queue = PacketQueue(queue_id="q_test", capacity_packets=2)

    p1 = Packet("p1", "r1", 0, 1, 1000.0, 0.0)
    p2 = Packet("p2", "r1", 1, 2, 1000.0, 1.0)
    p3 = Packet("p3", "r1", 2, 3, 1000.0, 2.0)

    # First two fit
    assert queue.enqueue(p1, 0.0) is True
    assert queue.enqueue(p2, 1.0) is True

    # Third overflows buffer
    assert queue.enqueue(p3, 2.0) is False
    assert queue.total_dropped == 1
    assert queue.size == 2

    # Dequeue p1
    item, wait = queue.dequeue(current_time_ms=5.0)
    assert item.packet_id == "p1"
    assert wait == 5.0
    assert queue.size == 1
