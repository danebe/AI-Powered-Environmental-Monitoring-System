"""
SIH 2026 Environmental Monitoring Network - Unit Tests
Analytics & Sensor Fusion Tests
"""

import unittest
import math
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.schemas import TelemetryPayload, SystemThresholds, SensorHealth
from app.analytics.normalization import SensorNormalizer
from app.analytics.anomaly_detector import ChannelAnomalyTracker, NodeAnomalyDetector
from app.analytics.fusion_engine import RiskFusionEngine


class TestSensorNormalization(unittest.TestCase):
    def test_rain_normalization(self):
        # 4095 is dry
        intensity, health = SensorNormalizer.normalize_rain(4095)
        self.assertEqual(intensity, 0.0)
        self.assertEqual(health, "ONLINE")

        # 600 or lower is torrential rain
        intensity, health = SensorNormalizer.normalize_rain(600)
        self.assertEqual(intensity, 100.0)

        # Invalid/noisy values
        intensity, health = SensorNormalizer.normalize_rain(5000)
        self.assertEqual(health, "INVALID")

    def test_gas_anomaly_normalization(self):
        # Baseline = 300
        mq2_norm, health = SensorNormalizer.normalize_gas_mq2(300, baseline=300)
        self.assertEqual(mq2_norm, 0.0)
        self.assertEqual(health, "ONLINE")

        # High reading = anomaly
        mq2_norm, health = SensorNormalizer.normalize_gas_mq2(2800, baseline=300)
        self.assertEqual(mq2_norm, 100.0)

    def test_missing_or_nan_data_resilience(self):
        # Test that NaNs/Infs in raw payload do not crash the normalizer
        payload = TelemetryPayload(
            temperature=float('nan'),
            humidity=float('inf'),
            water_level_cm=-50.0,
            rain_raw=4000
        )
        norm = SensorNormalizer.sanitize_and_normalize(payload)
        self.assertEqual(norm["temperature_c"], 25.0)
        self.assertEqual(norm["humidity_pct"], 50.0)
        self.assertEqual(norm["water_level_cm"], 0.0)
        self.assertEqual(norm["health_bme680"], "INVALID")
        self.assertEqual(norm["health_ultrasonic"], "INVALID")


class TestRiskFusionEngine(unittest.TestCase):
    def setUp(self):
        self.thresholds = SystemThresholds()
        self.engine = RiskFusionEngine(self.thresholds)
        self.anomaly_detector = NodeAnomalyDetector("TEST_NODE")

    def test_normal_baseline_scores(self):
        norm = {
            "temperature_c": 25.0,
            "humidity_pct": 55.0,
            "pressure_hpa": 1013.25,
            "gas_resistance_ohms": 140000.0,
            "water_level_cm": 10.0,
            "water_rate_of_rise_cm_min": 0.0,
            "rain_intensity_pct": 0.0,
            "mq2_anomaly_pct": 0.0,
            "mq7_anomaly_pct": 0.0,
            "flame_detected": False,
            "health_bme680": "ONLINE",
            "health_ultrasonic": "ONLINE",
            "health_rain": "ONLINE",
            "health_mq2": "ONLINE",
            "health_mq7": "ONLINE",
            "health_flame": "ONLINE"
        }
        stats = self.anomaly_detector.process(norm, timestamp=1000.0)
        scores = self.engine.evaluate_node(norm, stats)

        self.assertLess(scores.flood_score, 25.0)
        self.assertEqual(scores.flood_severity, "NORMAL")
        self.assertLess(scores.fire_score, 25.0)
        self.assertEqual(scores.fire_severity, "NORMAL")
        self.assertLess(scores.pollution_score, 25.0)
        self.assertEqual(scores.pollution_severity, "NORMAL")
        self.assertEqual(scores.highest_severity, "NORMAL")

    def test_critical_flood_detection_with_rate_of_rise(self):
        norm = {
            "temperature_c": 22.0,
            "humidity_pct": 95.0,
            "pressure_hpa": 1005.0,
            "gas_resistance_ohms": 120000.0,
            "water_level_cm": 75.0, # Above critical 65cm
            "water_rate_of_rise_cm_min": 8.5, # Flash flood rate
            "rain_intensity_pct": 90.0,
            "mq2_anomaly_pct": 0.0,
            "mq7_anomaly_pct": 0.0,
            "flame_detected": False,
            "health_bme680": "ONLINE",
            "health_ultrasonic": "ONLINE",
            "health_rain": "ONLINE",
            "health_mq2": "ONLINE",
            "health_mq7": "ONLINE",
            "health_flame": "ONLINE"
        }
        stats = self.anomaly_detector.process(norm, timestamp=1010.0)
        scores = self.engine.evaluate_node(norm, stats)

        self.assertGreaterEqual(scores.flood_score, 75.0)
        self.assertEqual(scores.flood_severity, "CRITICAL")
        self.assertEqual(scores.highest_hazard, "FLOOD")
        self.assertEqual(scores.highest_severity, "CRITICAL")
        self.assertTrue(any("rising rapidly" in r for r in scores.flood_reasons))

    def test_fire_detection_with_optical_flame(self):
        norm = {
            "temperature_c": 48.0,
            "humidity_pct": 25.0,
            "pressure_hpa": 1012.0,
            "gas_resistance_ohms": 80000.0,
            "water_level_cm": 5.0,
            "water_rate_of_rise_cm_min": 0.0,
            "rain_intensity_pct": 0.0,
            "mq2_anomaly_pct": 80.0,
            "mq7_anomaly_pct": 65.0,
            "flame_detected": True, # Optical flame confirmed
            "health_bme680": "ONLINE",
            "health_ultrasonic": "ONLINE",
            "health_rain": "ONLINE",
            "health_mq2": "ONLINE",
            "health_mq7": "ONLINE",
            "health_flame": "ONLINE"
        }
        stats = self.anomaly_detector.process(norm, timestamp=1020.0)
        scores = self.engine.evaluate_node(norm, stats)

        self.assertGreaterEqual(scores.fire_score, 75.0)
        self.assertEqual(scores.fire_severity, "CRITICAL")
        self.assertEqual(scores.highest_hazard, "FIRE")
        self.assertTrue(any("flame" in r.lower() for r in scores.fire_reasons))


if __name__ == "__main__":
    unittest.main()
