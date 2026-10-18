"""
Topology module for 5G two-tier edge/cloud network.
Defines explicit nodes, communication links, compute nodes, and candidate routing paths.
"""

from typing import Dict, List, Optional, Any
from mcra.models import (
    CommunicationLink,
    ComputeNode,
    Route,
    NodeTier,
    TopologyMode,
)


class NetworkTopology:
    """
    Explicit network topology graph:
    UEs -> Access Link -> Edge Router (gNB) ->
        [Edge Node] OR [Backhaul Link -> Cloud Node] -> Destination Sink
    """

    def __init__(
        self,
        access_link_capacity_mbps: float = 100.0,
        backhaul_capacity_mbps: float = 50.0,
        edge_compute_capacity: float = 30.0,
        cloud_compute_capacity: float = 150.0,
        queue_capacity_packets: int = 200,
    ):
        # 1. Physical / logical communication links
        self.link_access = CommunicationLink(
            link_id="link_access",
            src_node="ue",
            dst_node="edge_router",
            capacity_mbps=access_link_capacity_mbps,
            propagation_delay_ms=0.5,
            queue_capacity_packets=queue_capacity_packets,
        )

        self.link_edge = CommunicationLink(
            link_id="link_edge",
            src_node="edge_router",
            dst_node="edge_compute",
            capacity_mbps=access_link_capacity_mbps,
            propagation_delay_ms=0.2,
            queue_capacity_packets=queue_capacity_packets,
        )

        self.link_edge_sink = CommunicationLink(
            link_id="link_edge_sink",
            src_node="edge_compute",
            dst_node="destination",
            capacity_mbps=access_link_capacity_mbps,
            propagation_delay_ms=0.2,
            queue_capacity_packets=queue_capacity_packets,
        )

        self.link_backhaul = CommunicationLink(
            link_id="link_backhaul",
            src_node="edge_router",
            dst_node="cloud_compute",
            capacity_mbps=backhaul_capacity_mbps,
            propagation_delay_ms=12.0,  # Higher propagation delay over core/backhaul
            queue_capacity_packets=queue_capacity_packets,
        )

        self.link_cloud_sink = CommunicationLink(
            link_id="link_cloud_sink",
            src_node="cloud_compute",
            dst_node="destination",
            capacity_mbps=backhaul_capacity_mbps,
            propagation_delay_ms=1.0,
            queue_capacity_packets=queue_capacity_packets,
        )

        self.all_links: Dict[str, CommunicationLink] = {
            self.link_access.link_id: self.link_access,
            self.link_edge.link_id: self.link_edge,
            self.link_edge_sink.link_id: self.link_edge_sink,
            self.link_backhaul.link_id: self.link_backhaul,
            self.link_cloud_sink.link_id: self.link_cloud_sink,
        }

        # 2. Compute Nodes
        self.edge_compute = ComputeNode(
            node_id="edge_compute",
            tier=NodeTier.EDGE,
            capacity_units=edge_compute_capacity,
            base_delay_ms=0.5,
            queue_capacity_tasks=queue_capacity_packets,
        )

        self.cloud_compute = ComputeNode(
            node_id="cloud_compute",
            tier=NodeTier.CLOUD,
            capacity_units=cloud_compute_capacity,
            base_delay_ms=3.0,
            queue_capacity_tasks=queue_capacity_packets * 2,
        )

        self.all_compute_nodes: Dict[str, ComputeNode] = {
            self.edge_compute.node_id: self.edge_compute,
            self.cloud_compute.node_id: self.cloud_compute,
        }

        # 3. Canonical Routes
        self.route_edge = Route(
            route_id="route_edge",
            path_name="edge",
            links=[self.link_access, self.link_edge, self.link_edge_sink],
            compute_node=self.edge_compute,
        )

        self.route_cloud = Route(
            route_id="route_cloud",
            path_name="cloud",
            links=[self.link_access, self.link_backhaul, self.link_cloud_sink],
            compute_node=self.cloud_compute,
        )

    def get_candidate_routes(self, mode: TopologyMode) -> List[Route]:
        """Return legal candidate execution paths based on active topology mode."""
        if mode == TopologyMode.EDGE_ONLY:
            return [self.route_edge]
        elif mode == TopologyMode.CLOUD_ONLY:
            return [self.route_cloud]
        elif mode == TopologyMode.PARALLEL_HYBRID:
            # First try edge for low latency, then cloud fallback
            return [self.route_edge, self.route_cloud]
        else:
            return [self.route_edge]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize topology for UI diagram rendering."""
        nodes = [
            {"id": "ue", "label": "Traffic Source (UEs)", "type": "source"},
            {"id": "edge_router", "label": "Edge Router / gNB", "type": "router"},
            {"id": "edge_compute", "label": f"MEC Edge ({self.edge_compute.capacity_units} U/ms)", "type": "edge_compute"},
            {"id": "cloud_compute", "label": f"Central Cloud ({self.cloud_compute.capacity_units} U/ms)", "type": "cloud_compute"},
            {"id": "destination", "label": "Destination Sink", "type": "sink"},
        ]
        links = [
            {"id": l.link_id, "source": l.src_node, "target": l.dst_node, "capacity": l.capacity_mbps, "prop_delay_ms": l.propagation_delay_ms}
            for l in self.all_links.values()
        ]
        return {"nodes": nodes, "links": links}
