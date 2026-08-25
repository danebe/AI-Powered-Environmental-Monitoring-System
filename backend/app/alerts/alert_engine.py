"""
Environmental Intelligence Network
Alert and Event Engine with Hysteresis, Cooldown, Deduplication, and Multi-Tier Notification Routing
"""

from typing import Dict, Any, List, Optional
import time
from ..schemas import AlertEvent, HazardScoreBreakdown, SystemThresholds


class AlertEngine:
    """
    Prevents alert spamming via:
    1. Severity Hysteresis (Requires score to drop below lower threshold to clear alert)
    2. Cooldown Periods (Prevents re-triggering identical alert for N seconds)
    3. State Tracking (Updates ongoing incident instead of generating duplicates)
    4. Multi-Tier Notification Routing (CITIZEN / AUTHORITY / EMERGENCY)
    """

    def __init__(self, thresholds: SystemThresholds = None):
        self.thresholds = thresholds or SystemThresholds()
        # Active ongoing incidents keyed by (node_id:hazard_type)
        self.active_alerts: Dict[str, AlertEvent] = {}
        # Historical alert archive
        self.alert_history: List[AlertEvent] = []
        # Last emitted timestamp per (node_id:hazard_type)
        self.last_emitted_time: Dict[str, float] = {}

    def _determine_notification_tier(self, hazard_type: str, severity: str, score: float) -> str:
        """
        Routes alerts into appropriate response tiers:
        - CITIZEN: Advisory & public warning (all WARNING or general alerts)
        - AUTHORITY: Local municipal / law enforcement / fire department (CRITICAL events)
        - EMERGENCY: Regional disaster management (CRITICAL flood, fire, landslide, or multi-hazard > 85)
        """
        if severity == "CRITICAL":
            if hazard_type in ("FLOOD", "FIRE", "LANDSLIDE") or score >= 85.0:
                return "EMERGENCY"
            return "AUTHORITY"
        elif severity == "WARNING":
            if score >= 65.0:
                return "AUTHORITY"
            return "CITIZEN"
        return "CITIZEN"

    def process_node_scores(
        self,
        node_id: str,
        scores: HazardScoreBreakdown,
        norm_data: Dict[str, Any],
        timestamp: float = None
    ) -> List[AlertEvent]:
        now = timestamp or time.time()
        new_or_updated_events = []

        hazards = [
            ("FLOOD",      scores.flood_score,      scores.flood_severity,      scores.flood_reasons),
            ("FIRE",       scores.fire_score,        scores.fire_severity,       scores.fire_reasons),
            ("POLLUTION",  scores.pollution_score,   scores.pollution_severity,  scores.pollution_reasons),
            ("HEAT",       scores.heat_score,        scores.heat_severity,       scores.heat_reasons),
            ("LANDSLIDE",  scores.landslide_score,   scores.landslide_severity,  scores.landslide_reasons),
            ("INDUSTRIAL", scores.industrial_score,  scores.industrial_severity, scores.industrial_reasons),
        ]

        for h_type, score, severity, reasons in hazards:
            key = f"{node_id}:{h_type}"
            existing = self.active_alerts.get(key)
            last_time = self.last_emitted_time.get(key, 0.0)

            # Check if alert condition is active (WARNING or CRITICAL)
            if severity in ("WARNING", "CRITICAL"):
                tier = self._determine_notification_tier(h_type, severity, score)
                if existing is None:
                    # New event trigger!
                    if now - last_time >= self.thresholds.alert_cooldown_seconds:
                        event_id = f"EVT-{node_id[:4]}-{int(now)%100000:05d}-{h_type[:3]}"
                        event = AlertEvent(
                            event_id=event_id,
                            node_id=node_id,
                            hazard_type=h_type,
                            severity=severity,
                            score=score,
                            timestamp=now,
                            title=f"{severity} {h_type.replace('_', ' ')} ALERT",
                            reasons=reasons,
                            sensor_evidence={
                                "water_level_cm": norm_data.get("water_level_cm"),
                                "water_rate_of_rise_cm_min": norm_data.get("water_rate_of_rise_cm_min"),
                                "rain_intensity_pct": norm_data.get("rain_intensity_pct"),
                                "temperature_c": norm_data.get("temperature_c"),
                                "humidity_pct": norm_data.get("humidity_pct"),
                                "mq2_anomaly_pct": norm_data.get("mq2_anomaly_pct"),
                                "mq7_anomaly_pct": norm_data.get("mq7_anomaly_pct"),
                                "gas_resistance_ohms": norm_data.get("gas_resistance_ohms"),
                                "soil_moisture_pct": norm_data.get("soil_moisture_pct"),
                                "vibration_hits": norm_data.get("vibration_hits"),
                                "water_ph": norm_data.get("water_ph"),
                                "water_turbidity_ntu": norm_data.get("water_turbidity_ntu"),
                                "flame_detected": norm_data.get("flame_detected")
                            },
                            notification_tier=tier
                        )
                        self.active_alerts[key] = event
                        self.alert_history.append(event)
                        self.last_emitted_time[key] = now
                        new_or_updated_events.append(event)
                else:
                    # Ongoing incident: Update score, severity, tier and reasons
                    severity_escalated = (existing.severity == "WARNING" and severity == "CRITICAL")
                    existing.score = score
                    existing.reasons = reasons
                    existing.notification_tier = tier
                    if severity_escalated:
                        existing.severity = "CRITICAL"
                        existing.title = f"CRITICAL {h_type.replace('_', ' ')} ALERT (ESCALATED)"
                        new_or_updated_events.append(existing)

            else:
                # Severity dropped to LOW or NORMAL
                # Apply Hysteresis: Clear alert only if score drops firmly below (low_max - 5.0)
                if existing is not None and score < (self.thresholds.low_max - 5.0):
                    del self.active_alerts[key]

        return new_or_updated_events

    def acknowledge_alert(self, event_id: str, acknowledged_by: str = "Operator") -> bool:
        for evt in self.alert_history:
            if evt.event_id == event_id:
                evt.acknowledged = True
                evt.acknowledged_by = acknowledged_by
                evt.acknowledged_at = time.time()
                return True
        return False

    def clear_active_alerts(self):
        """Clear all currently active in-memory alerts (used when operator clicks Reset to Normal)."""
        self.active_alerts.clear()
        self.last_emitted_time.clear()

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        return [evt.to_dict() for evt in self.active_alerts.values()]

    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [evt.to_dict() for evt in reversed(self.alert_history[-limit:])]
