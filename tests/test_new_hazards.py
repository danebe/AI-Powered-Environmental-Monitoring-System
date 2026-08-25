"""
Environmental Intelligence Network - Unit Tests
7-Hazard Fusion Model Validation: Heat, Landslide, Industrial, Water Quality
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.schemas import TelemetryPayload, SystemThresholds
from app.analytics.normalization import SensorNormalizer
from app.analytics.anomaly_detector import NodeAnomalyDetector
from app.analytics.fusion_engine import RiskFusionEngine


class TestNewHazardModels(unittest.TestCase):
    def setUp(self):
        self.thresholds = SystemThresholds()
        self.engine = RiskFusionEngine(self.thresholds)
        self.detector = NodeAnomalyDetector("TEST_NODE")

    def test_extreme_heat_detection(self):
        norm = {
            "temperature_c": 52.5,
            "humidity_pct": 85.0,  # High RH amplifies heat stress
            "pressure_hpa": 1010.0,
            "gas_resistance_ohms": 120000.0,
            "water_level_cm": 5.0,
            "water_rate_of_rise_cm_min": 0.0,
            "rain_intensity_pct": 0.0,
            "mq2_anomaly_pct": 0.0,
            "mq7_anomaly_pct": 0.0,
            "soil_moisture_pct": 20.0,
            "vibration_hits": 0,
            "water_ph": 7.0,
            "water_turbidity_ntu": 5.0,
            "flame_detected": False,
            "health_bme680": "ONLINE",
            "health_ultrasonic": "ONLINE",
            "health_rain": "ONLINE",
            "health_mq2": "ONLINE",
            "health_mq7": "ONLINE",
            "health_flame": "ONLINE",
            "health_soil_moisture": "ONLINE",
            "health_vibration": "ONLINE"
        }
        stats = self.detector.process(norm, timestamp=1000.0)
        scores = self.engine.evaluate_node(norm, stats)

        self.assertGreaterEqual(scores.heat_score, 50.0)
        self.assertIn(scores.heat_severity, ["WARNING", "CRITICAL"])
        self.assertTrue(any("heat" in r.lower() or "temperature" in r.lower() for r in scores.heat_reasons))

    def test_landslide_precursor_detection(self):
        norm = {
            "temperature_c": 21.0,
            "humidity_pct": 92.0,
            "pressure_hpa": 1008.0,
            "gas_resistance_ohms": 130000.0,
            "water_level_cm": 15.0,
            "water_rate_of_rise_cm_min": 0.0,
            "rain_intensity_pct": 80.0,
            "mq2_anomaly_pct": 0.0,
            "mq7_anomaly_pct": 0.0,
            "soil_moisture_pct": 92.0,  # Critical saturation
            "vibration_hits": 45,       # Ground tremor hits
            "water_ph": 7.0,
            "water_turbidity_ntu": 15.0,
            "flame_detected": False,
            "health_bme680": "ONLINE",
            "health_ultrasonic": "ONLINE",
            "health_rain": "ONLINE",
            "health_mq2": "ONLINE",
            "health_mq7": "ONLINE",
            "health_flame": "ONLINE",
            "health_soil_moisture": "ONLINE",
            "health_vibration": "ONLINE"
        }
        # Run 3 consecutive samples to satisfy persistence filter
        scores = None
        for i in range(3):
            stats = self.detector.process(norm, timestamp=1000.0 + i)
            scores = self.engine.evaluate_node(norm, stats)

        self.assertGreaterEqual(scores.landslide_score, 70.0)
        self.assertEqual(scores.landslide_severity, "CRITICAL" if scores.landslide_score >= 75 else "WARNING")
        self.assertTrue(any("soil" in r.lower() or "vibration" in r.lower() for r in scores.landslide_reasons))

    def test_industrial_chemical_leak_detection(self):
        norm = {
            "temperature_c": 28.0,
            "humidity_pct": 50.0,
            "pressure_hpa": 1013.0,
            "gas_resistance_ohms": 12000.0,  # Plummeting VOC gas resistance
            "water_level_cm": 8.0,
            "water_rate_of_rise_cm_min": 0.0,
            "rain_intensity_pct": 0.0,
            "mq2_anomaly_pct": 75.0,        # Solvent / chemical vapors
            "mq7_anomaly_pct": 65.0,        # Elevated industrial CO
            "soil_moisture_pct": 30.0,
            "vibration_hits": 0,
            "water_ph": 7.0,
            "water_turbidity_ntu": 5.0,
            "flame_detected": False,
            "health_bme680": "ONLINE",
            "health_ultrasonic": "ONLINE",
            "health_rain": "ONLINE",
            "health_mq2": "ONLINE",
            "health_mq7": "ONLINE",
            "health_flame": "ONLINE",
            "health_soil_moisture": "ONLINE",
            "health_vibration": "ONLINE"
        }
        scores = None
        for i in range(3):
            stats = self.detector.process(norm, timestamp=2000.0 + i)
            scores = self.engine.evaluate_node(norm, stats)

        self.assertGreaterEqual(scores.industrial_score, 65.0)
        self.assertIn(scores.industrial_severity, ["WARNING", "CRITICAL"])
        self.assertEqual(scores.highest_hazard, "INDUSTRIAL")

    def test_water_quality_degradation(self):
        norm = {
            "temperature_c": 24.0,
            "humidity_pct": 70.0,
            "pressure_hpa": 1012.0,
            "gas_resistance_ohms": 120000.0,
            "water_level_cm": 35.0,
            "water_rate_of_rise_cm_min": 0.5,
            "rain_intensity_pct": 30.0,
            "mq2_anomaly_pct": 0.0,
            "mq7_anomaly_pct": 0.0,
            "soil_moisture_pct": 40.0,
            "vibration_hits": 0,
            "water_ph": 4.5,            # Highly acidic deviation from 7.0
            "water_turbidity_ntu": 250.0, # Muddy / contaminated
            "flame_detected": False,
            "health_bme680": "ONLINE",
            "health_ultrasonic": "ONLINE",
            "health_rain": "ONLINE",
            "health_mq2": "ONLINE",
            "health_mq7": "ONLINE",
            "health_flame": "ONLINE",
            "health_soil_moisture": "ONLINE",
            "health_vibration": "ONLINE"
        }
        stats = self.detector.process(norm, timestamp=3000.0)
        scores = self.engine.evaluate_node(norm, stats)

        self.assertGreaterEqual(scores.water_quality_score, 65.0)
        self.assertIn(scores.water_quality_severity, ["WARNING", "CRITICAL"])


if __name__ == "__main__":
    unittest.main()
