"""
SIH 2026 Environmental Monitoring Network - Unit Tests
Scenario Simulator Verification Tests
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.simulator.sim_engine import ScenarioSimulator
from app.analytics.normalization import SensorNormalizer
from app.analytics.anomaly_detector import NodeAnomalyDetector
from app.analytics.fusion_engine import RiskFusionEngine


class TestScenarioSimulator(unittest.TestCase):
    def setUp(self):
        self.sim = ScenarioSimulator()
        self.engine = RiskFusionEngine()
        self.detector = NodeAnomalyDetector("NODE_001")

    def test_all_scenarios_supported(self):
        expected = [
            "NORMAL", "HEAVY_RAIN", "RAPID_WATER_RISE", "FLOOD",
            "SMOKE_EVENT", "FIRE", "POLLUTION_EVENT", "SENSOR_FAILURE",
            "NODE_OFFLINE", "WIFI_FAILURE"
        ]
        for sc in expected:
            self.assertIn(sc, self.sim.SCENARIOS)
            ok = self.sim.set_scenario(sc, "NODE_001")
            self.assertTrue(ok)

    def test_flood_scenario_escalation(self):
        self.sim.set_scenario("FLOOD", "NODE_001")
        # Step through 5 packets
        last_scores = None
        for _ in range(5):
            pkt = self.sim.generate_next_packet("NODE_001")
            norm = SensorNormalizer.sanitize_and_normalize(pkt)
            stats = self.detector.process(norm, pkt.timestamp)
            last_scores = self.engine.evaluate_node(norm, stats)

        self.assertGreaterEqual(last_scores.flood_score, 65.0)
        self.assertIn(last_scores.flood_severity, ["WARNING", "CRITICAL"])

    def test_fire_scenario_escalation(self):
        self.sim.set_scenario("FIRE", "NODE_001")
        last_scores = None
        for _ in range(5):
            pkt = self.sim.generate_next_packet("NODE_001")
            norm = SensorNormalizer.sanitize_and_normalize(pkt)
            stats = self.detector.process(norm, pkt.timestamp)
            last_scores = self.engine.evaluate_node(norm, stats)

        self.assertGreaterEqual(last_scores.fire_score, 75.0)
        self.assertEqual(last_scores.fire_severity, "CRITICAL")
        self.assertEqual(last_scores.highest_hazard, "FIRE")


if __name__ == "__main__":
    unittest.main()
