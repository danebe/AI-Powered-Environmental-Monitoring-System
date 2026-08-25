"""
Environmental Intelligence Network - Unit Tests
Notification Engine & Tier Routing Tests
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.schemas import HazardScoreBreakdown, SystemThresholds
from app.alerts.alert_engine import AlertEngine
from app.notifications.notification_engine import NotificationEngine


class TestNotificationEngine(unittest.TestCase):
    def setUp(self):
        self.thresholds = SystemThresholds(alert_cooldown_seconds=10.0)
        self.alert_engine = AlertEngine(self.thresholds)
        self.notif_engine = NotificationEngine(self.alert_engine)

    def test_tier_routing_citizen_vs_authority_vs_emergency(self):
        # 1. Warning level alert -> CITIZEN tier
        scores_warn = HazardScoreBreakdown(
            heat_score=55.0,
            heat_severity="WARNING",
            heat_reasons=["High temperature"]
        )
        self.alert_engine.process_node_scores("NODE_001", scores_warn, {}, timestamp=100.0)
        citizen_notifs = self.notif_engine.get_notifications_by_tier("CITIZEN")
        self.assertEqual(len(citizen_notifs), 1)

        # 2. Critical Flood -> EMERGENCY tier
        scores_emerg = HazardScoreBreakdown(
            flood_score=90.0,
            flood_severity="CRITICAL",
            flood_reasons=["Catastrophic flood surge"]
        )
        self.alert_engine.process_node_scores("NODE_003", scores_emerg, {}, timestamp=105.0)
        emerg_notifs = self.notif_engine.get_notifications_by_tier("EMERGENCY")
        self.assertEqual(len(emerg_notifs), 1)

        # 3. Summary check
        summary = self.notif_engine.get_tier_summary()
        self.assertGreaterEqual(summary["TOTAL"], 2)


if __name__ == "__main__":
    unittest.main()
