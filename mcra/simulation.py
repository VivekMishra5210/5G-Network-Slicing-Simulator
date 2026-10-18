"""
Main discrete-event simulation orchestrator for the MCRA simulation mode.
Connects topology, resource ledger, traffic generator, event engine, and allocation logic.
"""

from typing import Dict, List, Optional, Any
from mcra.models import (
    TopologyMode,
    RequestStatus,
    EventType,
    ServiceRequest,
    Packet,
    Route,
    MCRADecisionTrace,
    ResourceType,
)
from mcra.topology import NetworkTopology
from mcra.resources import ResourceLedger
from mcra.event_engine import EventEngine
from mcra.traffic import MCRATrafficGenerator
from mcra.allocator import MCRAAllocator
from mcra.latency import serialization_delay_ms, propagation_delay_ms, compute_delay_ms
from mcra.metrics import MCRAMetricsEngine
from mcra.serialization import sanitize_for_json, format_csv_request_rows


class MCRASimulator:
    """
    Orchestrates the complete discrete-event MCRA simulation run.
    """

    def __init__(
        self,
        topology_mode: TopologyMode = TopologyMode.PARALLEL_HYBRID,
        seed: int = 42,
        cost_base: float = 2.0,
        comm_increment_mbps: float = 1.0,
        compute_increment_units: float = 0.5,
        access_link_capacity_mbps: float = 100.0,
        backhaul_capacity_mbps: float = 50.0,
        edge_compute_capacity: float = 30.0,
        cloud_compute_capacity: float = 150.0,
        queue_capacity_packets: int = 200,
        max_iterations: int = 50,
    ):
        self.topology_mode = topology_mode
        self.seed = seed
        self.cost_base = cost_base
        self.comm_increment_mbps = comm_increment_mbps
        self.compute_increment_units = compute_increment_units
        self.access_link_capacity_mbps = access_link_capacity_mbps
        self.backhaul_capacity_mbps = backhaul_capacity_mbps
        self.edge_compute_capacity = edge_compute_capacity
        self.cloud_compute_capacity = cloud_compute_capacity
        self.queue_capacity_packets = queue_capacity_packets
        self.max_iterations = max_iterations

    def run(
        self,
        scenario: str = "normal_mix",
        duration_ms: float = 1000.0,
        num_tenants: int = 2,
        arrival_rate_scale: float = 1.0,
        max_events_to_return: int = 300,
    ) -> Dict[str, Any]:
        """
        Execute the discrete-event MCRA simulation.
        Returns a JSON-safe dictionary containing summary, per-slice, per-tenant,
        event logs, requests, decisions, and topology visualization metadata.
        """
        # 1. Instantiate Core Subsystems
        topology = NetworkTopology(
            access_link_capacity_mbps=self.access_link_capacity_mbps,
            backhaul_capacity_mbps=self.backhaul_capacity_mbps,
            edge_compute_capacity=self.edge_compute_capacity,
            cloud_compute_capacity=self.cloud_compute_capacity,
            queue_capacity_packets=self.queue_capacity_packets,
        )

        ledger = ResourceLedger()
        for link in topology.all_links.values():
            ledger.register_resource(link.link_id, link.capacity_mbps, ResourceType.COMMUNICATION, min_unit=1.0)
        for node in topology.all_compute_nodes.values():
            ledger.register_resource(node.node_id, node.capacity_units, ResourceType.COMPUTATION, min_unit=0.5)

        engine = EventEngine()
        allocator = MCRAAllocator(
            cost_base=self.cost_base,
            comm_increment_mbps=self.comm_increment_mbps,
            compute_increment_units=self.compute_increment_units,
            max_iterations=self.max_iterations,
        )

        traffic_gen = MCRATrafficGenerator(seed=self.seed)
        candidate_routes = topology.get_candidate_routes(self.topology_mode)

        # 2. Generate Traffic Trace
        requests = traffic_gen.generate_trace(
            scenario=scenario,
            duration_ms=duration_ms,
            num_tenants=num_tenants,
            arrival_rate_scale=arrival_rate_scale,
        )

        requests_by_id: Dict[str, ServiceRequest] = {r.request_id: r for r in requests}
        all_packets: List[Packet] = []
        for r in requests:
            all_packets.extend(r.packets)

        # Schedule initial arrival events
        for r in requests:
            engine.schedule(
                time_ms=r.arrival_time_ms,
                event_type=EventType.REQUEST_ARRIVAL,
                request_id=r.request_id,
            )

        decision_traces: List[MCRADecisionTrace] = []
        iterations_log: List[int] = []

        # Tracking server availability to avoid simultaneous packet collisions on same resource
        link_busy_until: Dict[str, float] = {l_id: 0.0 for l_id in topology.all_links.keys()}
        compute_busy_until: Dict[str, float] = {c_id: 0.0 for c_id in topology.all_compute_nodes.keys()}

        # Map route candidates by path_name for quick lookup
        routes_by_name: Dict[str, Route] = {r.path_name: r for r in candidate_routes}

        # 3. Discrete Event Simulation Loop
        while engine.has_events():
            event = engine.pop_next()
            current_t = engine.current_time_ms
            req = requests_by_id.get(event.request_id)
            if not req:
                continue

            if event.event_type == EventType.REQUEST_ARRIVAL:
                # Run MCRA admission decision
                admitted, selected_route, plan, pred_delay, trace, status = allocator.admit_request(
                    request=req,
                    candidate_routes=candidate_routes,
                    ledger=ledger,
                    current_time_ms=current_t,
                )
                decision_traces.append(trace)
                iterations_log.append(len(trace.iterations))

                if admitted and selected_route:
                    req.status = RequestStatus.ADMITTED
                    req.route_candidate = selected_route.path_name
                    engine.schedule(
                        time_ms=current_t,
                        event_type=EventType.REQUEST_ADMITTED,
                        request_id=req.request_id,
                        metadata={"route": selected_route.path_name, "pred_delay_ms": round(pred_delay, 2)},
                    )

                    # Start packet transmission along the route
                    # Route flow: Link 0 (access) -> Link 1 (edge or backhaul) -> Compute -> Link 2 (sink)
                    first_link = selected_route.links[0]
                    for pkt in req.packets:
                        # Schedule packet arrival at first link
                        start_tx = max(current_t, link_busy_until[first_link.link_id])
                        bw = req.allocated_resources.get(first_link.link_id, first_link.capacity_mbps)
                        tx_time = serialization_delay_ms(pkt.payload_bits, bw)
                        prop_time = propagation_delay_ms(first_link)
                        finish_tx = start_tx + tx_time + prop_time
                        link_busy_until[first_link.link_id] = finish_tx

                        engine.schedule(
                            time_ms=finish_tx,
                            event_type=EventType.LINK_SERVICE_COMPLETED,
                            request_id=req.request_id,
                            packet_id=pkt.packet_id,
                            node_or_link_id=first_link.link_id,
                            metadata={"hop_index": 0, "link_id": first_link.link_id},
                        )
                else:
                    req.status = status
                    req.status_reason = trace.status_reason
                    engine.schedule(
                        time_ms=current_t,
                        event_type=EventType.REQUEST_BLOCKED,
                        request_id=req.request_id,
                        metadata={"reason": trace.status_reason},
                    )

            elif event.event_type == EventType.LINK_SERVICE_COMPLETED:
                hop_idx = event.metadata.get("hop_index", 0)
                pkt_id = event.packet_id
                active_route = routes_by_name.get(req.route_candidate)
                if not active_route:
                    continue

                if hop_idx == 0:
                    # Traversed access link -> now traverse second link towards compute node
                    next_link = active_route.links[1]
                    start_tx = max(current_t, link_busy_until[next_link.link_id])
                    bw = req.allocated_resources.get(next_link.link_id, next_link.capacity_mbps)
                    pkt = next((p for p in req.packets if p.packet_id == pkt_id), None)
                    payload = pkt.payload_bits if pkt else 10000.0

                    tx_time = serialization_delay_ms(payload, bw)
                    prop_time = propagation_delay_ms(next_link)
                    finish_tx = start_tx + tx_time + prop_time
                    link_busy_until[next_link.link_id] = finish_tx

                    engine.schedule(
                        time_ms=finish_tx,
                        event_type=EventType.LINK_SERVICE_COMPLETED,
                        request_id=req.request_id,
                        packet_id=pkt_id,
                        node_or_link_id=next_link.link_id,
                        metadata={"hop_index": 1, "link_id": next_link.link_id},
                    )

                elif hop_idx == 1:
                    # Traversed link into compute node -> now process compute task
                    c_node = active_route.compute_node
                    start_comp = max(current_t, compute_busy_until[c_node.node_id])
                    comp_rate = req.allocated_resources.get(c_node.node_id, c_node.capacity_units)
                    d_comp = compute_delay_ms(req.compute_demand, comp_rate, c_node.base_delay_ms)
                    finish_comp = start_comp + d_comp
                    compute_busy_until[c_node.node_id] = finish_comp

                    engine.schedule(
                        time_ms=finish_comp,
                        event_type=EventType.COMPUTE_SERVICE_COMPLETED,
                        request_id=req.request_id,
                        packet_id=pkt_id,
                        node_or_link_id=c_node.node_id,
                        metadata={"compute_node": c_node.node_id},
                    )

                elif hop_idx == 2:
                    # Final link to sink completed -> packet delivered!
                    pkt = next((p for p in req.packets if p.packet_id == pkt_id), None)
                    if pkt:
                        pkt.delivered = True
                        pkt.delivery_time_ms = current_t

                    engine.schedule(
                        time_ms=current_t,
                        event_type=EventType.PACKET_DELIVERED,
                        request_id=req.request_id,
                        packet_id=pkt_id,
                        node_or_link_id="destination",
                    )

            elif event.event_type == EventType.COMPUTE_SERVICE_COMPLETED:
                # Compute completed -> now traverse egress sink link
                active_route = routes_by_name.get(req.route_candidate)
                if not active_route:
                    continue

                sink_link = active_route.links[2]
                pkt_id = event.packet_id
                start_tx = max(current_t, link_busy_until[sink_link.link_id])
                bw = req.allocated_resources.get(sink_link.link_id, sink_link.capacity_mbps)
                pkt = next((p for p in req.packets if p.packet_id == pkt_id), None)
                payload = pkt.payload_bits if pkt else 10000.0

                tx_time = serialization_delay_ms(payload, bw)
                prop_time = propagation_delay_ms(sink_link)
                finish_tx = start_tx + tx_time + prop_time
                link_busy_until[sink_link.link_id] = finish_tx

                engine.schedule(
                    time_ms=finish_tx,
                    event_type=EventType.LINK_SERVICE_COMPLETED,
                    request_id=req.request_id,
                    packet_id=pkt_id,
                    node_or_link_id=sink_link.link_id,
                    metadata={"hop_index": 2, "link_id": sink_link.link_id},
                )

            elif event.event_type == EventType.PACKET_DELIVERED:
                # Check if all packets belonging to this request have been delivered
                if all(p.delivered for p in req.packets):
                    req.status = RequestStatus.COMPLETED
                    req.completion_time_ms = current_t
                    req.actual_e2e_delay_ms = max(0.0, req.completion_time_ms - req.arrival_time_ms)

                    # Release reserved resources in ledger
                    if req.reservation_id:
                        ledger.release(req.reservation_id, current_time_ms=current_t)
                        engine.schedule(
                            time_ms=current_t,
                            event_type=EventType.RESOURCE_RELEASED,
                            request_id=req.request_id,
                            metadata={"reservation_id": req.reservation_id},
                        )

        # 4. Post-Simulation Metric Computation
        # Compute metrics over the simulation time horizon
        metrics = MCRAMetricsEngine.compute_all_metrics(
            requests=requests,
            all_packets=all_packets,
            ledger=ledger,
            total_duration_ms=duration_ms,
            iterations_log=iterations_log,
        )

        # Build bounded event log for frontend display
        events_output = [ev.to_dict() for ev in engine.event_log[:max_events_to_return]]

        # Build resource timeseries for graphs
        resource_timeseries = {}
        for res_id, entry in ledger.resources.items():
            resource_timeseries[res_id] = [
                {"time_ms": round(t, 2), "used": round(u, 3), "capacity": entry.total_capacity}
                for t, u in entry.history
            ]

        # Top decisions for inspector
        decisions_output = [d.to_dict() for d in decision_traces[:30]]

        csv_rows = format_csv_request_rows(requests)

        raw_result = {
            "metadata": {
                "algorithm": "MCRA",
                "topology_mode": self.topology_mode.value,
                "scenario": scenario,
                "duration_ms": duration_ms,
                "seed": self.seed,
                "cost_base": self.cost_base,
                "comm_increment_mbps": self.comm_increment_mbps,
                "compute_increment_units": self.compute_increment_units,
                "total_events_processed": len(engine.event_log),
                "model_assumptions": [
                    "Discrete-event queue with explicit serialization, propagation, and compute delay",
                    "Exponential marginal cost model from Lin et al. (Sensors 2023)",
                    "Atomic all-or-nothing multi-resource reservations with zero capacity leakage",
                    "Educational packet-flow network abstraction",
                ],
            },
            "summary": metrics["summary"],
            "per_slice": metrics["per_slice"],
            "per_tenant": metrics["per_tenant"],
            "resource_utilization": metrics["resource_utilization"],
            "resource_timeseries": resource_timeseries,
            "requests": csv_rows,
            "events": events_output,
            "mcra_decisions": decisions_output,
            "topology": topology.to_dict(),
        }

        return sanitize_for_json(raw_result)
