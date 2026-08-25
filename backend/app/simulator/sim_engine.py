"""
Environmental Intelligence Network
Multi-Scenario Sensor Physics Simulator — 15 Scenarios Across 4 Environmental Zones
"""

from typing import Dict, Any, List
import time
import math
import random
from ..schemas import TelemetryPayload, Location, SensorHealth


class ScenarioSimulator:
    """
    Generates realistic, physically consistent sensor streams for 4 distributed nodes:
    - NODE_001: Industrial Zone (VOC, Chemical gases, CO)
    - NODE_002: Forest Edge (Wildfire, Heat, Smoke)
    - NODE_003: Coastal / River Basin (Flooding, Water surge, Water Quality)
    - NODE_004: Hillside (Landslide, Soil Saturation, Vibration)
    """

    SCENARIOS = [
        "NORMAL",
        "HEAVY_RAIN",
        "RAPID_WATER_RISE",
        "FLOOD",
        "SMOKE_EVENT",
        "FIRE",
        "POLLUTION_EVENT",
        "EXTREME_HEAT",
        "LANDSLIDE_PRECURSOR",
        "INDUSTRIAL_LEAK",
        "WATER_CONTAMINATION",
        "MULTI_HAZARD",
        "SENSOR_FAILURE",
        "NODE_OFFLINE",
        "WIFI_FAILURE"
    ]

    def __init__(self):
        self.active_scenario: str = "NORMAL"
        self.target_node_id: str = "NODE_001"
        self.scenario_start_time: float = time.time()
        self.step_count: int = 0

        # Zone-specific nominal baseline states
        self.node_states: Dict[str, Dict[str, Any]] = {
            # NODE_001: Industrial Zone (slightly higher background gases)
            "NODE_001": {
                "water": 10.0, "temp": 28.5, "hum": 55.0,
                "mq2": 420, "mq7": 350, "bme_res": 95000.0, "rain_raw": 4000,
                "soil": 25.0, "vibration": 0, "ph": 7.1, "turbidity": 8.0
            },
            # NODE_002: Forest Edge (clean air, natural temp swings)
            "NODE_002": {
                "water": 8.0, "temp": 25.0, "hum": 62.0,
                "mq2": 280, "mq7": 240, "bme_res": 145000.0, "rain_raw": 3950,
                "soil": 38.0, "vibration": 0, "ph": 7.0, "turbidity": 4.0
            },
            # NODE_003: River / Coastal Basin (higher moisture & water baseline)
            "NODE_003": {
                "water": 18.0, "temp": 24.5, "hum": 72.0,
                "mq2": 290, "mq7": 250, "bme_res": 130000.0, "rain_raw": 3850,
                "soil": 55.0, "vibration": 0, "ph": 7.2, "turbidity": 12.0
            },
            # NODE_004: Hillside Terrain (dryer soil baseline, vibration sensitive)
            "NODE_004": {
                "water": 6.0, "temp": 23.5, "hum": 58.0,
                "mq2": 270, "mq7": 230, "bme_res": 150000.0, "rain_raw": 4020,
                "soil": 32.0, "vibration": 0, "ph": 6.9, "turbidity": 5.0
            }
        }

    def set_scenario(self, scenario: str, node_id: str = "NODE_001") -> bool:
        if scenario in self.SCENARIOS:
            self.active_scenario = scenario
            self.target_node_id = node_id
            self.scenario_start_time = time.time()
            self.step_count = 0
            return True
        return False

    def generate_next_packet(self, node_id: str) -> TelemetryPayload:
        self.step_count += 1
        now = time.time()
        state = self.node_states[node_id]

        is_target = (node_id == self.target_node_id)
        current_scenario = self.active_scenario if is_target else "NORMAL"

        health = SensorHealth()
        flame = False
        water_rate = 0.0
        vibration_hits = 0

        # Base ambient natural variations
        state["temp"] += random.uniform(-0.08, 0.08)
        state["hum"] += random.uniform(-0.15, 0.15)
        state["bme_res"] += random.uniform(-400.0, 400.0)

        # -------------------------------------------------------------
        # Physical Scenario Transformations
        # -------------------------------------------------------------
        if current_scenario == "NORMAL":
            state["water"] = max(5.0, min(22.0, state["water"] + random.uniform(-0.1, 0.1)))
            state["rain_raw"] = int(max(3800, min(4095, state["rain_raw"] + random.randint(-10, 10))))
            state["mq2"] = int(max(260, min(450, state["mq2"] + random.randint(-4, 4))))
            state["mq7"] = int(max(220, min(380, state["mq7"] + random.randint(-4, 4))))
            state["soil"] = max(20.0, min(60.0, state["soil"] + random.uniform(-0.2, 0.2)))
            state["ph"] = round(max(6.8, min(7.4, state["ph"] + random.uniform(-0.02, 0.02))), 2)
            state["turbidity"] = max(2.0, min(15.0, state["turbidity"] + random.uniform(-0.3, 0.3)))
            flame = False
            vibration_hits = random.choice([0, 0, 0, 1])

        elif current_scenario == "HEAVY_RAIN":
            state["rain_raw"] = int(max(850, state["rain_raw"] - 300))
            state["hum"] = min(96.0, state["hum"] + 1.2)
            state["soil"] = min(80.0, state["soil"] + 1.5)
            water_rate = 1.2
            state["water"] += 0.5
            state["turbidity"] = min(40.0, state["turbidity"] + 2.0)

        elif current_scenario == "RAPID_WATER_RISE":
            state["rain_raw"] = 720
            state["hum"] = 98.0
            water_rate = 6.8
            state["water"] += 2.2
            state["turbidity"] = min(90.0, state["turbidity"] + 6.0)

        elif current_scenario == "FLOOD":
            state["rain_raw"] = 600
            state["hum"] = 99.0
            state["water"] = min(88.0, state["water"] + 1.8)
            water_rate = 4.8
            state["turbidity"] = min(180.0, state["turbidity"] + 8.0)

        elif current_scenario == "SMOKE_EVENT":
            state["mq2"] = int(min(2600, state["mq2"] + 180))
            state["mq7"] = int(min(1800, state["mq7"] + 120))
            state["temp"] = min(36.0, state["temp"] + 0.4)
            state["hum"] = max(35.0, state["hum"] - 0.8)
            flame = False

        elif current_scenario == "FIRE":
            flame = True
            state["temp"] = min(68.0, state["temp"] + 3.2)
            state["hum"] = max(20.0, state["hum"] - 2.5)
            state["mq2"] = int(min(3800, state["mq2"] + 320))
            state["mq7"] = int(min(3200, state["mq7"] + 260))

        elif current_scenario == "POLLUTION_EVENT":
            state["bme_res"] = max(12000.0, state["bme_res"] - 7500.0)
            state["mq7"] = int(min(2900, state["mq7"] + 190))
            state["mq2"] = int(min(2200, state["mq2"] + 130))

        elif current_scenario == "EXTREME_HEAT":
            state["temp"] = min(54.0, state["temp"] + 1.8)
            state["hum"] = min(88.0, state["hum"] + 0.5)  # Heat index amplification
            state["bme_res"] = max(60000.0, state["bme_res"] - 2000.0)

        elif current_scenario == "LANDSLIDE_PRECURSOR":
            state["soil"] = min(92.0, state["soil"] + 3.0)  # Saturated ground
            state["rain_raw"] = 700                         # Heavy rain
            vibration_hits = min(65, vibration_hits + random.randint(18, 42))  # Seismic / tremor hits

        elif current_scenario == "INDUSTRIAL_LEAK":
            state["bme_res"] = max(8000.0, state["bme_res"] - 12000.0)  # Plummeting gas resistance
            state["mq2"] = int(min(3400, state["mq2"] + 300))
            state["mq7"] = int(min(3100, state["mq7"] + 250))

        elif current_scenario == "WATER_CONTAMINATION":
            state["ph"] = max(4.6, state["ph"] - 0.25)        # Acidic plume
            state["turbidity"] = min(320.0, state["turbidity"] + 28.0)  # Murky toxic runoff
            state["water"] = min(45.0, state["water"] + 0.8)

        elif current_scenario == "MULTI_HAZARD":
            # Concurrent: Flash Flood + Industrial Chemical Leak
            state["water"] = min(82.0, state["water"] + 2.0)
            water_rate = 5.5
            state["rain_raw"] = 650
            state["bme_res"] = max(11000.0, state["bme_res"] - 9000.0)
            state["mq2"] = int(min(3100, state["mq2"] + 260))
            state["mq7"] = int(min(2800, state["mq7"] + 220))
            state["turbidity"] = min(220.0, state["turbidity"] + 15.0)

        elif current_scenario == "SENSOR_FAILURE":
            health.ultrasonic = "INVALID"
            health.mq2 = "DEGRADED"
            health.bme680 = "OFFLINE"
            health.soil_moisture = "INVALID"
            state["water"] = 999.0

        elif current_scenario in ("WIFI_FAILURE", "NODE_OFFLINE"):
            pass

        # Soil moisture raw ADC (FC-28 inverted mapping)
        soil_pct = state["soil"]
        soil_raw = int(3500.0 - (soil_pct / 100.0) * (3500.0 - 800.0))

        # Node coordinates
        latitudes = {"NODE_001": 28.6080, "NODE_002": 28.6139, "NODE_003": 28.6185, "NODE_004": 28.6020}
        longitudes = {"NODE_001": 77.2280, "NODE_002": 77.2090, "NODE_003": 77.2150, "NODE_004": 77.2010}

        payload = TelemetryPayload(
            node_id=node_id,
            timestamp=now,
            sequence_id=self.step_count,
            location=Location(
                latitude=latitudes.get(node_id, 28.6139),
                longitude=longitudes.get(node_id, 77.2090)
            ),
            temperature=round(state["temp"], 2),
            humidity=round(state["hum"], 1),
            pressure=round(1012.5 + random.uniform(-0.4, 0.4), 1),
            gas_resistance=round(state["bme_res"], 1),
            mq2_raw=int(state["mq2"]),
            mq7_raw=int(state["mq7"]),
            rain_raw=int(state["rain_raw"]),
            water_level_raw=int(min(4095, state["water"] * 35)),
            water_level_cm=round(state["water"], 2),
            water_rate_of_rise_cm_min=round(water_rate, 2),
            soil_moisture_raw=soil_raw,
            soil_moisture_pct=round(state["soil"], 1),
            vibration_hits=vibration_hits,
            water_ph=round(state["ph"], 2),
            water_turbidity_ntu=round(state["turbidity"], 1),
            flame_detected=flame,
            signal_strength=-62 + random.randint(-3, 3),
            sensor_health=health
        )

        return payload
