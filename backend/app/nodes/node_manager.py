"""
SIH 2026 Environmental Monitoring Network
Multi-Node Management and Health State Tracker
"""

from typing import Dict, Any, List, Optional
import time
from ..schemas import NodeMetadata, Location, TelemetryPayload, HazardScoreBreakdown


class NodeManager:
    """
    Tracks registered nodes in the mesh/network:
    NODE_001 -> Forest Edge (Wildfire & Flood watch)
    NODE_002 -> Drainage Channel (Flash Flood monitor)
    NODE_003 -> Industrial Zone (VOC & Chemical Gas monitor)
    NODE_004 -> Residential Area (Air Quality & Rain monitor)
    """

    NODE_TIMEOUT_SECONDS = 15.0  # Mark OFFLINE if no telemetry received for 15s

    def __init__(self):
        self.nodes: Dict[str, NodeMetadata] = {}
        self._init_default_nodes()

    def _init_default_nodes(self):
        defaults = [
            NodeMetadata(
                node_id="NODE_001",
                name="Forest Edge Node (North)",
                location=Location(latitude=28.6139, longitude=77.2090, altitude_m=216.0, zone_description="Northern Forest Boundary")
            ),
            NodeMetadata(
                node_id="NODE_002",
                name="Drainage Channel Node (Culvert 4)",
                location=Location(latitude=28.6185, longitude=77.2150, altitude_m=208.0, zone_description="Lowland Drainage Basin")
            ),
            NodeMetadata(
                node_id="NODE_003",
                name="Industrial Zone Node (East)",
                location=Location(latitude=28.6080, longitude=77.2280, altitude_m=212.0, zone_description="Chemical & Manufacturing Sector")
            ),
            NodeMetadata(
                node_id="NODE_004",
                name="Residential Area Node (South Sector)",
                location=Location(latitude=28.6020, longitude=77.2010, altitude_m=219.0, zone_description="Dense Urban Habitat")
            )
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
                node_id=payload.node_id,
                name=f"Field Node {payload.node_id}",
                location=payload.location
            )
            self.nodes[payload.node_id] = node

        node.last_seen = payload.timestamp
        node.firmware_version = payload.firmware_version
        node.battery_voltage = payload.battery_voltage
        node.signal_strength = payload.signal_strength
        node.active_alerts_count = active_alerts_for_node
        node.latest_scores = scores
        node.status = "ONLINE"

    def check_health_states(self, now: float = None) -> None:
        current_time = now or time.time()
        for node in self.nodes.values():
            time_since = current_time - node.last_seen
            if time_since > self.NODE_TIMEOUT_SECONDS:
                node.status = "OFFLINE"
            elif time_since > 8.0:
                node.status = "DEGRADED"
            else:
                node.status = "ONLINE"

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        self.check_health_states()
        return [node.to_dict() for node in self.nodes.values()]

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        self.check_health_states()
        node = self.nodes.get(node_id)
        return node.to_dict() if node else None
