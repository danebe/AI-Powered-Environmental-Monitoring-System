"""
Environmental Intelligence Network
Statistical Anomaly Detector: EMA, Rolling Std, Rate-of-Change, Persistence Filter
"""

from typing import Dict, Any
import math
from collections import deque


class ChannelAnomalyTracker:
    """
    Tracks time-series statistics for a single sensor channel per node:
    EMA, rolling standard deviation, rate of change, consecutive anomaly counter.
    """

    def __init__(self, name: str, window_size: int = 30, alpha: float = 0.2):
        self.name       = name
        self.window_size = window_size
        self.alpha      = alpha
        self.history    = deque(maxlen=window_size)
        self.ema:   float = 0.0
        self.initialized: bool  = False
        self.prev_val:    float = 0.0
        self.prev_time:   float = 0.0
        self.consecutive_anomalies: int = 0

    def update(self, val: float, timestamp: float) -> Dict[str, Any]:
        if not self.initialized:
            self.ema = val
            self.prev_val  = val
            self.prev_time = timestamp
            self.initialized = True
            self.history.append(val)
            return {"val": val, "ema": val, "std_dev": 0.0, "z_score": 0.0,
                    "rate_of_change_per_min": 0.0, "is_outlier": False, "consecutive": 0}

        self.ema = (self.alpha * val) + ((1.0 - self.alpha) * self.ema)
        self.history.append(val)

        mean = sum(self.history) / len(self.history)
        variance = sum((x - mean) ** 2 for x in self.history) / len(self.history)
        std_dev  = math.sqrt(variance)

        z_score = ((val - mean) / std_dev) if std_dev > 1e-4 else 0.0
        is_outlier = abs(z_score) > 3.0

        dt = max(0.1, timestamp - self.prev_time)
        rate_of_change = ((val - self.prev_val) / dt) * 60.0
        self.prev_val  = val
        self.prev_time = timestamp

        self.consecutive_anomalies = (
            self.consecutive_anomalies + 1
            if (is_outlier or abs(z_score) > 2.0)
            else max(0, self.consecutive_anomalies - 1)
        )

        return {
            "val":                  round(val, 2),
            "ema":                  round(self.ema, 2),
            "std_dev":              round(std_dev, 2),
            "z_score":              round(z_score, 2),
            "rate_of_change_per_min": round(rate_of_change, 2),
            "is_outlier":           is_outlier,
            "consecutive":          self.consecutive_anomalies,
        }

    def reset(self, val: float) -> None:
        """Snap EMA and history to a known baseline value (e.g. on scenario NORMAL reset)."""
        self.ema = val
        self.prev_val = val
        self.initialized = True
        self.consecutive_anomalies = 0
        self.history.clear()
        self.history.append(val)


class NodeAnomalyDetector:
    """
    Maintains anomaly tracking across all sensor channels for a specific node.
    """

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.channels = {
            "temperature":     ChannelAnomalyTracker("temperature",     alpha=0.20),
            "water_level":     ChannelAnomalyTracker("water_level",     alpha=0.30),
            "mq2_smoke":       ChannelAnomalyTracker("mq2_smoke",       alpha=0.15),
            "mq7_co":          ChannelAnomalyTracker("mq7_co",          alpha=0.15),
            "gas_res":         ChannelAnomalyTracker("gas_res",         alpha=0.20),
            "rain":            ChannelAnomalyTracker("rain",            alpha=0.25),
            "soil_moisture":   ChannelAnomalyTracker("soil_moisture",   alpha=0.20),
            "vibration":       ChannelAnomalyTracker("vibration",       alpha=0.30),
            "water_ph":        ChannelAnomalyTracker("water_ph",        alpha=0.15),
            "water_turbidity": ChannelAnomalyTracker("water_turbidity", alpha=0.20),
        }

    def process(self, norm_data: Dict[str, Any], timestamp: float) -> Dict[str, Any]:
        return {
            "temperature":     self.channels["temperature"]    .update(norm_data["temperature_c"],        timestamp),
            "water_level":     self.channels["water_level"]    .update(norm_data["water_level_cm"],       timestamp),
            "mq2_smoke":       self.channels["mq2_smoke"]      .update(norm_data["mq2_anomaly_pct"],      timestamp),
            "mq7_co":          self.channels["mq7_co"]         .update(norm_data["mq7_anomaly_pct"],      timestamp),
            "gas_res":         self.channels["gas_res"]        .update(norm_data["gas_resistance_ohms"],  timestamp),
            "rain":            self.channels["rain"]           .update(norm_data["rain_intensity_pct"],   timestamp),
            "soil_moisture":   self.channels["soil_moisture"]  .update(norm_data["soil_moisture_pct"],    timestamp),
            "vibration":       self.channels["vibration"]      .update(float(norm_data["vibration_hits"]),timestamp),
            "water_ph":        self.channels["water_ph"]       .update(norm_data["water_ph"],             timestamp),
            "water_turbidity": self.channels["water_turbidity"].update(norm_data["water_turbidity_ntu"],  timestamp),
        }

    def reset_to_baseline(self, temp: float = 30.0, water: float = 12.0,
                          mq2: float = 0.0, mq7: float = 0.0,
                          gas_res: float = 120000.0, rain: float = 0.0,
                          soil: float = 35.0, vib: float = 0.0) -> None:
        """Snap all channel EMAs/history to baseline values on NORMAL reset."""
        self.channels["temperature"]    .reset(temp)
        self.channels["water_level"]    .reset(water)
        self.channels["mq2_smoke"]      .reset(mq2)
        self.channels["mq7_co"]         .reset(mq7)
        self.channels["gas_res"]        .reset(gas_res)
        self.channels["rain"]           .reset(rain)
        self.channels["soil_moisture"]  .reset(soil)
        self.channels["vibration"]      .reset(vib)
        self.channels["water_ph"]       .reset(7.0)
        self.channels["water_turbidity"].reset(0.0)
