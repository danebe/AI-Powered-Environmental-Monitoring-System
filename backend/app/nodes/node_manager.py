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

    NODE_001 — Industrial Zone   (chemical leaks, VOC, CO emissions)
    NODE_002 — Forest Edge       (wildfire, smoke, extreme heat)
    NODE_003 — Coastal / River   (flooding, flash flood, water quality)
    NODE_004 — Hillside          (landslide precursors, soil saturation, vibration)
    """

    NODE_TIMEOUT_SECONDS = 15.0

    def __init__(self):
        self.nodes: Dict[str, NodeMetadata] = {}
        self._init_default_nodes()

    def _init_default_nodes(self):
        defaults = [
            NodeMetadata(
                node_id   = "NODE_001",
                name      = "Industrial Zone Node",
                zone_type = "INDUSTRIAL",
                location  = Location(
                    latitude=28.6080, longitude=77.2280, altitude_m=212.0,
                    zone_description="Chemical & Manufacturing Sector"
                )
            ),
            NodeMetadata(
                node_id   = "NODE_002",
                name      = "Forest Edge Node",
                zone_type = "FOREST",
                location  = Location(
                    latitude=28.6139, longitude=77.2090, altitude_m=216.0,
                    zone_description="Northern Forest Boundary"
                )
            ),
            NodeMetadata(
                node_id   = "NODE_003",
                name      = "Coastal / River Basin Node",
                zone_type = "RIVER",
                location  = Location(
                    latitude=28.6185, longitude=77.2150, altitude_m=208.0,
                    zone_description="Flood-Prone Lowland River Channel"
                )
            ),
            NodeMetadata(
                node_id   = "NODE_004",
                name      = "Hillside Node",
                zone_type = "AGRICULTURAL",
                location  = Location(
                    latitude=28.6020, longitude=77.2010, altitude_m=260.0,
                    zone_description="Landslide-Prone Hillside Terrain"
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
