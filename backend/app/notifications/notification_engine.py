"""
Environmental Intelligence Network
Notification Engine: Multi-Tier Community and Authority Dispatcher
"""

from typing import Dict, Any, List, Optional
import time
from ..schemas import AlertEvent


class NotificationEngine:
    """
    Categorizes alerts into three distinct action tiers:
    - CITIZEN: Community SMS / Web advisory broadcast (evacuation advice, air safety)
    - AUTHORITY: First-responder dashboard dispatch (Fire dept, Police, Medical)
    - EMERGENCY: State disaster management rapid deployment team
    """

    def __init__(self, alert_engine):
        self.alert_engine = alert_engine

    def get_notifications_by_tier(self, tier: str = "ALL") -> List[Dict[str, Any]]:
        """
        Returns active & recent notifications filtered by target audience tier.
        tier: 'ALL' | 'CITIZEN' | 'AUTHORITY' | 'EMERGENCY'
        """
        history = self.alert_engine.get_alert_history(limit=50)
        active = self.alert_engine.get_active_alerts()

        # Combine active and history, de-duplicating by event_id
        seen = set()
        combined = []

        for item in active + history:
            eid = item["event_id"]
            if eid not in seen:
                seen.add(eid)
                item_tier = item.get("notification_tier", "CITIZEN")
                if tier == "ALL" or item_tier.upper() == tier.upper():
                    combined.append(item)

        return combined

    def get_tier_summary(self) -> Dict[str, int]:
        active = self.alert_engine.get_active_alerts()
        summary = {"CITIZEN": 0, "AUTHORITY": 0, "EMERGENCY": 0, "TOTAL": len(active)}
        for a in active:
            t = a.get("notification_tier", "CITIZEN")
            if t in summary:
                summary[t] += 1
            else:
                summary["CITIZEN"] += 1
        return summary
