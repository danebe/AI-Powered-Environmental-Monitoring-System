"""
SIH 2026 Environmental Monitoring Network
Multi-Scenario Sensor Physics Simulator
"""

from typing import Dict, Any, List
import time
import math
import random
from ..schemas import TelemetryPayload, Location, SensorHealth


class ScenarioSimulator:
    """
    Generates realistic, physically consistent sensor streams for 4 distributed nodes
    under various emergency and fault injection scenarios.
    """

    SCENARIOS = [
        "NORMAL",
        "HEAVY_RAIN",
        "RAPID_WATER_RISE",
        "FLOOD",
        "SMOKE_EVENT",
        "FIRE",
        "POLLUTION_EVENT",
        "SENSOR_FAILURE",
        "NODE_OFFLINE",
        "WIFI_FAILURE"
    ]

    def __init__(self):
        self.active_scenario: str = "NORMAL"
        self.target_node_id: str = "NODE_001"
        self.scenario_start_time: float = time.time()
        self.step_count: int = 0

        # State memory for smooth continuous physics
        self.node_states: Dict[str, Dict[str, Any]] = {
            "NODE_001": {"water": 12.0, "temp": 26.5, "hum": 62.0, "mq2": 320, "mq7": 280, "bme_res": 120000.0, "rain_raw": 3950},
            "NODE_002": {"water": 18.0, "temp": 25.8, "hum": 68.0, "mq2": 310, "mq7": 270, "bme_res": 135000.0, "rain_raw": 3900},
            "NODE_003": {"water": 10.0, "temp": 28.0, "hum": 55.0, "mq2": 450, "mq7": 380, "bme_res": 95000.0, "rain_raw": 4000},
            "NODE_004": {"water": 8.0, "temp": 26.0, "hum": 60.0, "mq2": 300, "mq7": 260, "bme_res": 140000.0, "rain_raw": 4020}
        }

    def set_scenario(self, scenario: str, node_id: str = "NODE_001"):
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
        elapsed = now - self.scenario_start_time
        state = self.node_states[node_id]

        is_target = (node_id == self.target_node_id)
        current_scenario = self.active_scenario if is_target else "NORMAL"

        health = SensorHealth()
        flame = False
        water_rate = 0.0

        # Base nominal ambient perturbations
        state["temp"] += random.uniform(-0.1, 0.1)
        state["hum"] += random.uniform(-0.2, 0.2)
        state["bme_res"] += random.uniform(-500.0, 500.0)

        # -------------------------------------------------------------
        # Scenario Physics Simulation
        # -------------------------------------------------------------
        if current_scenario == "NORMAL":
            state["water"] = max(8.0, min(15.0, state["water"] + random.uniform(-0.1, 0.1)))
            state["rain_raw"] = int(max(3800, min(4095, state["rain_raw"] + random.randint(-15, 15))))
            state["mq2"] = int(max(280, min(380, state["mq2"] + random.randint(-5, 5))))
            state["mq7"] = int(max(240, min(320, state["mq7"] + random.randint(-5, 5))))
            state["bme_res"] = max(110000.0, min(160000.0, state["bme_res"]))
            flame = False

        elif current_scenario == "HEAVY_RAIN":
            # Rain drops sharply (low raw ADC = heavy rain)
            state["rain_raw"] = int(max(900, state["rain_raw"] - 350))
            state["hum"] = min(96.0, state["hum"] + 1.5)
            # Water level slowly starts responding
            water_rate = 1.2
            state["water"] += 0.4

        elif current_scenario == "RAPID_WATER_RISE":
            # Severe rain + sudden surge wave
            state["rain_raw"] = 750
            state["hum"] = 98.0
            water_rate = 6.8  # Rapid +6.8 cm/min rise
            state["water"] += 2.2

        elif current_scenario == "FLOOD":
            # Full critical flood state: water well above critical threshold (e.g. 78 cm)
            state["rain_raw"] = 620
            state["hum"] = 99.0
            state["water"] = min(88.0, state["water"] + 1.5)
            water_rate = 4.5

        elif current_scenario == "SMOKE_EVENT":
            # Rising smoke anomaly on MQ-2 and MQ-7 without open flame
            state["mq2"] = int(min(2600, state["mq2"] + 180))
            state["mq7"] = int(min(1800, state["mq7"] + 120))
            state["temp"] = min(36.0, state["temp"] + 0.4)
            state["hum"] = max(38.0, state["hum"] - 1.0)
            flame = False

        elif current_scenario == "FIRE":
            # Open blaze: Flame sensor active, high thermal spike, dense combustion gas
            flame = True
            state["temp"] = min(68.0, state["temp"] + 3.5)
            state["hum"] = max(22.0, state["hum"] - 3.0)
            state["mq2"] = int(min(3800, state["mq2"] + 350))
            state["mq7"] = int(min(3200, state["mq7"] + 280))

        elif current_scenario == "POLLUTION_EVENT":
            # Severe VOC and CO chemical plume
            state["bme_res"] = max(14000.0, state["bme_res"] - 8000.0) # Sharp drop in gas resistance
            state["mq7"] = int(min(2900, state["mq7"] + 200))
            state["mq2"] = int(min(2200, state["mq2"] + 140))

        elif current_scenario == "SENSOR_FAILURE":
            # Simulate degraded and invalid sensors
            health.ultrasonic = "INVALID"
            health.mq2 = "DEGRADED"
            health.bme680 = "OFFLINE"
            state["water"] = 999.0 # Impossible physical value handled gracefully by normalizer

        elif current_scenario == "WIFI_FAILURE" or current_scenario == "NODE_OFFLINE":
            # Telemetry will be dropped by network handler
            pass

        # Package payload
        payload = TelemetryPayload(
            node_id=node_id,
            timestamp=now,
            sequence_id=self.step_count,
            temperature=round(state["temp"], 2),
            humidity=round(state["hum"], 1),
            pressure=round(1012.5 + random.uniform(-0.5, 0.5), 1),
            gas_resistance=round(state["bme_res"], 1),
            mq2_raw=int(state["mq2"]),
            mq7_raw=int(state["mq7"]),
            rain_raw=int(state["rain_raw"]),
            water_level_raw=int(min(4095, state["water"] * 35)),
            water_level_cm=round(state["water"], 2),
            water_rate_of_rise_cm_min=round(water_rate, 2),
            flame_detected=flame,
            battery_voltage=3.82,
            signal_strength=-62 + random.randint(-4, 4),
            sensor_health=health
        )

        return payload
