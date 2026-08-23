"""
SIH 2026 Environmental Monitoring Network - Unit Tests
Alert Engine, Hysteresis, Cooldown, and Deduplication Tests
"""

import unittest
import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.schemas import HazardScoreBreakdown, SystemThresholds
from app.alerts.alert_engine import AlertEngine


class TestAlertEngine(unittest.TestCase):
    def setUp(self):
        self.thresholds = SystemThresholds(alert_cooldown_seconds=30.0)
        self.engine = AlertEngine(self.thresholds)

    def test_alert_generation_and_cooldown_deduplication(self):
        # 1. Trigger first warning
        scores1 = HazardScoreBreakdown(
            flood_score=68.0,
            flood_severity="WARNING",
            flood_reasons=["Water level elevated"]
        )
        norm_data = {"water_level_cm": 42.0}

        events1 = self.engine.process_node_scores("NODE_001", scores1, norm_data, timestamp=100.0)
        self.assertEqual(len(events1), 1)
        self.assertEqual(events1[0].severity, "WARNING")
        self.assertEqual(events1[0].hazard_type, "FLOOD")

        # 2. Subsequent reading within cooldown should update existing event rather than spawning new IDs
        scores2 = HazardScoreBreakdown(
            flood_score=72.0,
            flood_severity="WARNING",
            flood_reasons=["Water level elevated further"]
        )
        events2 = self.engine.process_node_scores("NODE_001", scores2, norm_data, timestamp=105.0)
        # Should not generate a brand new duplicate event ID
        self.assertEqual(len(events2), 0)
        active = self.engine.get_active_alerts()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["score"], 72.0)

    def test_severity_escalation(self):
        # Initial warning
        scores1 = HazardScoreBreakdown(flood_score=60.0, flood_severity="WARNING", flood_reasons=["Rising water"])
        self.engine.process_node_scores("NODE_002", scores1, {}, timestamp=200.0)

        # Escalation to CRITICAL
        scores2 = HazardScoreBreakdown(flood_score=85.0, flood_severity="CRITICAL", flood_reasons=["Flash flood surge"])
        events = self.engine.process_node_scores("NODE_002", scores2, {}, timestamp=205.0)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].severity, "CRITICAL")
        self.assertIn("ESCALATED", events[0].title)

    def test_hysteresis_clearing(self):
        # Start in warning
        scores1 = HazardScoreBreakdown(flood_score=65.0, flood_severity="WARNING")
        self.engine.process_node_scores("NODE_003", scores1, {}, timestamp=300.0)
        self.assertEqual(len(self.engine.get_active_alerts()), 1)

        # Score drops to 48 (still in Low zone, above hysteresis threshold of 44)
        scores2 = HazardScoreBreakdown(flood_score=48.0, flood_severity="LOW")
        self.engine.process_node_scores("NODE_003", scores2, {}, timestamp=305.0)
        # Alert remains active to prevent bouncing
        self.assertEqual(len(self.engine.get_active_alerts()), 1)

        # Score drops firmly to 30
        scores3 = HazardScoreBreakdown(flood_score=30.0, flood_severity="LOW")
        self.engine.process_node_scores("NODE_003", scores3, {}, timestamp=310.0)
        # Alert cleared by hysteresis!
        self.assertEqual(len(self.engine.get_active_alerts()), 0)

    def test_acknowledgement(self):
        scores = HazardScoreBreakdown(fire_score=88.0, fire_severity="CRITICAL", fire_reasons=["Flame confirmed"])
        events = self.engine.process_node_scores("NODE_004", scores, {}, timestamp=400.0)
        event_id = events[0].event_id

        # Acknowledge
        ok = self.engine.acknowledge_alert(event_id, acknowledged_by="Operator Bravo")
        self.assertTrue(ok)
        history = self.engine.get_alert_history()
        self.assertTrue(history[0]["acknowledged"])
        self.assertEqual(history[0]["acknowledged_by"], "Operator Bravo")


if __name__ == "__main__":
    unittest.main()
