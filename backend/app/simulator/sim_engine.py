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

        # Zone-specific nominal baseline states tailored for Chennai
        self.node_states: Dict[str, Dict[str, Any]] = {
            # NODE_001: Manali Industrial Estate (North Chennai chemical/petroleum corridor)
            "NODE_001": {
                "water": 12.0, "temp": 32.5, "hum": 68.0,
                "mq2": 420, "mq7": 350, "bme_res": 85000.0, "rain_raw": 4000,
                "soil": 28.0, "vibration": 0
            },
            # NODE_002: Guindy National Park (Urban reserve, dense tree canopy)
            "NODE_002": {
                "water": 10.0, "temp": 30.0, "hum": 72.0,
                "mq2": 280, "mq7": 240, "bme_res": 145000.0, "rain_raw": 3950,
                "soil": 42.0, "vibration": 0
            },
            # NODE_003: Adyar River Estuary / Besant Nagar (Coastal lowlands & drainage)
            "NODE_003": {
                "water": 20.0, "temp": 29.5, "hum": 80.0,
                "mq2": 290, "mq7": 250, "bme_res": 130000.0, "rain_raw": 3900,
                "soil": 58.0, "vibration": 0
            },
            # NODE_004: Pallavaram Hills / Tambaram Ridge (Steep terrain, rocky slopes)
            "NODE_004": {
                "water": 8.0, "temp": 31.0, "hum": 65.0,
                "mq2": 270, "mq7": 230, "bme_res": 150000.0, "rain_raw": 4020,
                "soil": 35.0, "vibration": 0
            }
        }

    # Chennai baseline values (used on NORMAL reset)
    _BASELINES: Dict[str, Dict[str, Any]] = {
        "NODE_001": {"water": 12.0, "temp": 32.5, "hum": 68.0, "mq2": 420, "mq7": 350, "bme_res": 85000.0,  "rain_raw": 4000, "soil": 28.0},
        "NODE_002": {"water": 10.0, "temp": 30.0, "hum": 72.0, "mq2": 280, "mq7": 240, "bme_res": 145000.0, "rain_raw": 3950, "soil": 42.0},
        "NODE_003": {"water": 20.0, "temp": 29.5, "hum": 80.0, "mq2": 290, "mq7": 250, "bme_res": 130000.0, "rain_raw": 3900, "soil": 58.0},
        "NODE_004": {"water":  8.0, "temp": 31.0, "hum": 65.0, "mq2": 270, "mq7": 230, "bme_res": 150000.0, "rain_raw": 4020, "soil": 35.0},
    }

    def set_scenario(self, scenario: str, node_id: str = "NODE_001") -> bool:
        if scenario in self.SCENARIOS:
            prev = self.active_scenario
            self.active_scenario = scenario
            self.target_node_id = node_id
            self.scenario_start_time = time.time()
            self.step_count = 0
            # On reset to NORMAL: snap ALL node states back to clean baselines
            # so heat/gas/water values don't linger after an extreme scenario
            if scenario == "NORMAL":
                for nid, baseline in self._BASELINES.items():
                    state = self.node_states[nid]
                    for key, val in baseline.items():
                        state[key] = val
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

        # Base ambient natural variations for coastal tropical Chennai
        state["temp"] += random.uniform(-0.06, 0.06)
        state["hum"] += random.uniform(-0.12, 0.12)
        state["bme_res"] += random.uniform(-350.0, 350.0)

        # -------------------------------------------------------------
        # Physical Scenario Transformations (Chennai Environmental Dynamics)
        # -------------------------------------------------------------
        if current_scenario == "NORMAL":
            # Instant decay back to zone-specific nominal Chennai baseline
            base = self._BASELINES[node_id]
            state["temp"]     = base["temp"]     + (state["temp"]     - base["temp"])     * 0.2 + random.uniform(-0.05, 0.05)
            state["hum"]      = base["hum"]      + (state["hum"]      - base["hum"])      * 0.2 + random.uniform(-0.10, 0.10)
            state["bme_res"]  = base["bme_res"]  + (state["bme_res"]  - base["bme_res"])  * 0.2 + random.uniform(-200.0, 200.0)
            state["soil"]     = base["soil"]     + (state["soil"]     - base["soil"])     * 0.2 + random.uniform(-0.15, 0.15)
            state["water"]    = base["water"]    + (state["water"]    - base["water"])    * 0.2 + random.uniform(-0.10, 0.10)
            state["mq2"]      = int(base["mq2"]  + (state["mq2"]      - base["mq2"])      * 0.2 + random.randint(-3, 3))
            state["mq7"]      = int(base["mq7"]  + (state["mq7"]      - base["mq7"])      * 0.2 + random.randint(-3, 3))
            state["rain_raw"] = int(base["rain_raw"] + (state["rain_raw"] - base["rain_raw"]) * 0.2 + random.randint(-5, 5))
            flame = False
            vibration_hits = random.choice([0, 0, 0, 1])

        elif current_scenario == "HEAVY_RAIN":
            # Northeast Monsoon torrential rain across Chennai
            state["rain_raw"] = int(max(680, state["rain_raw"] - 350))
            state["hum"] = min(98.0, state["hum"] + 1.5)
            state["soil"] = min(88.0, state["soil"] + 2.0)
            water_rate = 2.4
            state["water"] = min(60.0, state["water"] + 1.2)
            # Monsoon rain triggers hill vibration and landslide warning at NODE_004
            if node_id == "NODE_004" or self.target_node_id == "NODE_004":
                vibration_hits = random.randint(12, 22)
                state["soil"] = min(94.0, state["soil"] + 3.0)

        elif current_scenario == "RAPID_WATER_RISE":
            # Cyclone surge / Adyar River flash surge (+6.8 cm/min)
            state["rain_raw"] = 620
            state["hum"] = 99.0
            water_rate = 6.8
            state["water"] = min(95.0, state["water"] + 2.8)
            state["soil"] = min(96.0, state["soil"] + 2.5)
            # Water surge and runoff causes ground destabilization / landslide risk on hills
            if node_id == "NODE_004" or self.target_node_id == "NODE_004":
                vibration_hits = random.randint(20, 35)

        elif current_scenario == "FLOOD":
            # Severe Urban Inundation (2015/2023 Chennai Cyclone Michaung pattern)
            state["rain_raw"] = 500
            state["hum"] = 99.5
            state["water"] = min(120.0, state["water"] + 2.2)
            water_rate = 5.2
            state["soil"] = min(98.0, state["soil"] + 1.0)
            # Torrential cyclone flooding triggers critical slope destabilization on Pallavaram hills
            if node_id == "NODE_004" or self.target_node_id == "NODE_004":
                vibration_hits = random.randint(25, 42)

        elif current_scenario == "SMOKE_EVENT":
            state["mq2"] = int(min(2600, state["mq2"] + 180))
            state["mq7"] = int(min(1800, state["mq7"] + 120))
            state["temp"] = min(38.0, state["temp"] + 0.4)
            state["hum"] = max(40.0, state["hum"] - 0.8)
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
            # Chennai peak summer Kathiri Veyyil heat wave
            state["temp"] = min(54.0, state["temp"] + 1.8)
            state["hum"] = min(88.0, state["hum"] + 0.5)  # Heat index amplification
            state["bme_res"] = max(55000.0, state["bme_res"] - 2000.0)

        elif current_scenario == "LANDSLIDE_PRECURSOR":
            # Coupled Ground Saturation + Tremor Vibration in Pallavaram Hills
            # NOTE: water level kept at shallow baseline (9.0 cm) and moderate rain (2800 raw)
            # so water/flood score stays in NORMAL (10-18 pts), while landslide scores CRITICAL (90+ pts)
            state["soil"] = min(98.0, state["soil"] + 4.0)   # Critical ground saturation >90% -> 40pts
            state["rain_raw"] = 2800                         # Moderate wet conditions, NOT flood deluge
            state["hum"] = min(82.0, state["hum"] + 0.5)     # Mild rain humidity
            state["water"] = 9.0                             # Normal shallow hillside drainage level
            water_rate = 0.0                                 # No flood surge
            vibration_hits = min(68, vibration_hits + random.randint(30, 52))  # Slope slip seismic pulses

        elif current_scenario == "INDUSTRIAL_LEAK":
            state["bme_res"] = max(8000.0, state["bme_res"] - 12000.0)  # Plummeting gas resistance in Manali
            state["mq2"] = int(min(3400, state["mq2"] + 300))
            state["mq7"] = int(min(3100, state["mq7"] + 250))

        elif current_scenario == "MULTI_HAZARD":
            # Severe compound crisis: Cyclone Flood Surge + Manali Industrial Gas Release
            state["water"] = min(88.0, state["water"] + 2.2)
            water_rate = 5.8
            state["rain_raw"] = 580
            state["soil"] = min(95.0, state["soil"] + 2.0)
            state["bme_res"] = max(11000.0, state["bme_res"] - 9000.0)
            state["mq2"] = int(min(3100, state["mq2"] + 260))
            state["mq7"] = int(min(2800, state["mq7"] + 220))
            if node_id == "NODE_004" or self.target_node_id == "NODE_004":
                vibration_hits = random.randint(25, 40)

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
        latitudes  = {"NODE_001": 13.1700, "NODE_002": 13.0067, "NODE_003": 12.9985, "NODE_004": 12.9675}
        longitudes = {"NODE_001": 80.2620, "NODE_002": 80.2206, "NODE_003": 80.2537, "NODE_004": 80.1514}

        payload = TelemetryPayload(
            node_id=node_id,
            timestamp=now,
            sequence_id=self.step_count,
            location=Location(
                latitude=latitudes.get(node_id, 13.0850),
                longitude=longitudes.get(node_id, 80.2101)
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
            water_ph=7.0,
            water_turbidity_ntu=0.0,
            flame_detected=flame,
            signal_strength=-62 + random.randint(-3, 3),
            sensor_health=health
        )

        return payload
