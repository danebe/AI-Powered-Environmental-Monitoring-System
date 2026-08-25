"""
Environmental Intelligence Network
Edge AI Inference Validator & Confidence Model
"""

from typing import Dict, Any, Tuple


class EdgeAIPredictor:
    """
    Simulates embedded on-device decision logic and validates confidence against cloud analytics.
    Evaluates sensor anomaly vectors to generate a confidence score and detect sensor drift.
    """

    @staticmethod
    def evaluate_edge_inference(norm_data: Dict[str, Any], cloud_scores: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compares edge sensor vector against expected physical bounds to assess model confidence.
        """
        confidence_factors = []

        # 1. Atmospheric sensor stability
        temp = norm_data.get("temperature_c", 25.0)
        hum = norm_data.get("humidity_pct", 50.0)
        if 15.0 <= temp <= 45.0 and 20.0 <= hum <= 85.0:
            confidence_factors.append(0.95)
        else:
            confidence_factors.append(0.80)

        # 2. Gas sensor baseline coherence
        mq2 = norm_data.get("mq2_anomaly_pct", 0.0)
        mq7 = norm_data.get("mq7_anomaly_pct", 0.0)
        if abs(mq2 - mq7) < 40.0:
            confidence_factors.append(0.92)
        else:
            confidence_factors.append(0.78)

        # 3. Ground sensor stability
        soil = norm_data.get("soil_moisture_pct", 30.0)
        vib = norm_data.get("vibration_hits", 0)
        if soil <= 90.0 and vib < 50:
            confidence_factors.append(0.94)
        else:
            confidence_factors.append(0.85)

        avg_confidence = sum(confidence_factors) / len(confidence_factors)

        # Drift detection: high anomaly without correlated channels
        highest_score = cloud_scores.get("highest_score", 0.0)
        highest_hazard = cloud_scores.get("highest_hazard", "NONE")

        drift_flag = False
        drift_reason = "No sensor drift detected"

        if highest_score > 60.0 and avg_confidence < 0.80:
            drift_flag = True
            drift_reason = "Multi-sensor cross-validation variance high; verifying with cloud EMA"

        return {
            "edge_confidence_score": round(avg_confidence * 100.0, 1),
            "edge_decision_state": "EDGE_NOMINAL" if highest_score < 50.0 else f"EDGE_{highest_hazard}",
            "sensor_drift_detected": drift_flag,
            "drift_diagnostic": drift_reason,
            "inference_mode": "EDGE_AUTONOMOUS"
        }
