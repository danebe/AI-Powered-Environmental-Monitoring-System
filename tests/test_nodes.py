"""
SIH 2026 Environmental Monitoring Network - Unit Tests
Multi-Node Management & Health Tracker Tests
"""

import unittest
import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.schemas import TelemetryPayload, HazardScoreBreakdown
from app.nodes.node_manager import NodeManager


class TestNodeManager(unittest.TestCase):
    def setUp(self):
        self.mgr = NodeManager()

    def test_default_nodes_registered(self):
        nodes = self.mgr.get_all_nodes()
        self.assertEqual(len(nodes), 4)
        node_ids = [n["node_id"] for n in nodes]
        self.assertIn("NODE_001", node_ids)
        self.assertIn("NODE_002", node_ids)
        self.assertIn("NODE_003", node_ids)
        self.assertIn("NODE_004", node_ids)

    def test_node_heartbeat_and_timeout(self):
        payload = TelemetryPayload(
            node_id="NODE_001",
            timestamp=1000.0,
            battery_voltage=3.85,
            signal_strength=-60
        )
        scores = HazardScoreBreakdown(highest_score=15.0, highest_severity="NORMAL")
        self.mgr.update_node_heartbeat(payload, scores, 0)

        # Fresh check
        node = self.mgr.get_node("NODE_001")
        self.assertEqual(node["status"], "ONLINE")
        self.assertEqual(node["battery_voltage"], 3.85)

        # Timeout after 16 seconds
        self.mgr.check_health_states(now=1016.0)
        node_after = self.mgr.get_node("NODE_001")
        self.assertEqual(node_after["status"], "OFFLINE")


if __name__ == "__main__":
    unittest.main()
