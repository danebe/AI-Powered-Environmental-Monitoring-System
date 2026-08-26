"""
Environmental Intelligence Network
Multi-Node Management and Health State Tracker
"""

from typing import Dict, Any, List, Optional
import time
from ..schemas import NodeMetadata, Location, TelemetryPayload, HazardScoreBreakdown


class NodeManager:
    """
    4-node registry representing distinct environmental deployment zones.

    NODE_001 — Manali Industrial Estate, North Chennai  (petrochemical, VOC, CO, TNPCB zone)
    NODE_002 — Guindy National Park, Chennai            (wildfire, smoke, extreme heat, forest edge)
    NODE_003 — Adyar River Estuary, Besant Nagar        (flash flood, coastal surge, water quality)
    NODE_004 — Pallavaram Hills, Tambaram               (landslide, soil saturation, ground vibration)
    """

    NODE_TIMEOUT_SECONDS = 15.0

    def __init__(self):
        self.nodes: Dict[str, NodeMetadata] = {}
        self._init_default_nodes()

    def _init_default_nodes(self):
        defaults = [
            NodeMetadata(
                node_id   = "NODE_001",
                name      = "Manali Industrial Estate",
                zone_type = "INDUSTRIAL",
                location  = Location(
                    latitude=13.1700, longitude=80.2620, altitude_m=8.0,
                    zone_description="TNPCB Petrochemical & Fertilizer Cluster, North Chennai"
                )
            ),
            NodeMetadata(
                node_id   = "NODE_002",
                name      = "Guindy National Park",
                zone_type = "FOREST",
                location  = Location(
                    latitude=13.0067, longitude=80.2206, altitude_m=22.0,
                    zone_description="Urban Forest Reserve — Only National Park Inside an Indian Metro"
                )
            ),
            NodeMetadata(
                node_id   = "NODE_003",
                name      = "Adyar River Estuary",
                zone_type = "RIVER",
                location  = Location(
                    latitude=12.9985, longitude=80.2537, altitude_m=3.0,
                    zone_description="Coastal Flood Zone — Adyar Estuary & Besant Nagar, Cyclone Vardah Impact Area"
                )
            ),
            NodeMetadata(
                node_id   = "NODE_004",
                name      = "Pallavaram Hills",
                zone_type = "AGRICULTURAL",
                location  = Location(
                    latitude=12.9675, longitude=80.1514, altitude_m=75.0,
                    zone_description="Landslide-Sensitive Elevated Terrain — Pallavaram–Tambaram Ridge"
                )
            ),
        ]
        for node in defaults:
            self.nodes[node.node_id] = node

    def update_node_heartbeat(
        self,
        payload: TelemetryPayload,
        scores: HazardScoreBreakdown,
        active_alerts_for_node: int
    ):
        node = self.nodes.get(payload.node_id)
        if not node:
            node = NodeMetadata(
                node_id   = payload.node_id,
                name      = f"Field Node {payload.node_id}",
                zone_type = "URBAN",
                location  = payload.location
            )
            self.nodes[payload.node_id] = node

        node.last_seen           = payload.timestamp
        node.firmware_version    = payload.firmware_version
        node.signal_strength     = payload.signal_strength
        node.active_alerts_count = active_alerts_for_node
        node.latest_scores       = scores
        node.status              = "ONLINE"

    def check_health_states(self, now: float = None):
        t = now or time.time()
        for node in self.nodes.values():
            elapsed = t - node.last_seen
            if elapsed > self.NODE_TIMEOUT_SECONDS:
                node.status = "OFFLINE"
            elif elapsed > 8.0:
                node.status = "DEGRADED"
            else:
                node.status = "ONLINE"

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        self.check_health_states()
        return [n.to_dict() for n in self.nodes.values()]

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        self.check_health_states()
        node = self.nodes.get(node_id)
        return node.to_dict() if node else None
