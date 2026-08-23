"""
SIH 2026 Environmental Monitoring Network
Statistical Anomaly Detector: EMA, Rolling Std, Rate-of-Change, Persistence Filter
"""

from typing import Dict, Any, List
import math
from collections import deque


class ChannelAnomalyTracker:
    """
    Tracks time-series statistics for a single metric channel per node:
    - Exponential Moving Average (EMA)
    - Rolling window history for standard deviation
    - Rate of change (derivative)
    - Consecutive anomaly persistence counter
    """
    def __init__(self, name: str, window_size: int = 30, alpha: float = 0.2):
        self.name = name
        self.window_size = window_size
        self.alpha = alpha
        self.history = deque(maxlen=window_size)
        self.ema: float = 0.0
        self.initialized: bool = False
        self.prev_val: float = 0.0
        self.prev_time: float = 0.0
        self.consecutive_anomalies: int = 0

    def update(self, val: float, timestamp: float) -> Dict[str, Any]:
        if not self.initialized:
            self.ema = val
            self.prev_val = val
            self.prev_time = timestamp
            self.initialized = True
            self.history.append(val)
            return {
                "val": val,
                "ema": val,
                "std_dev": 0.0,
                "z_score": 0.0,
                "rate_of_change_per_min": 0.0,
                "is_outlier": False,
                "consecutive": 0
            }

        # 1. Update EMA
        self.ema = (self.alpha * val) + ((1.0 - self.alpha) * self.ema)
        self.history.append(val)

        # 2. Compute Rolling Standard Deviation
        mean = sum(self.history) / len(self.history)
        variance = sum((x - mean) ** 2 for x in self.history) / len(self.history)
        std_dev = math.sqrt(variance)

        # 3. Z-Score outlier detection
        z_score = 0.0
        if std_dev > 1e-4:
            z_score = (val - mean) / std_dev

        is_outlier = abs(z_score) > 3.0

        # 4. Rate of change (per minute)
        dt = max(0.1, timestamp - self.prev_time)
        rate_of_change = ((val - self.prev_val) / dt) * 60.0

        self.prev_val = val
        self.prev_time = timestamp

        # 5. Persistence counter
        if is_outlier or abs(z_score) > 2.0:
            self.consecutive_anomalies += 1
        else:
            self.consecutive_anomalies = max(0, self.consecutive_anomalies - 1)

        return {
            "val": round(val, 2),
            "ema": round(self.ema, 2),
            "std_dev": round(std_dev, 2),
            "z_score": round(z_score, 2),
            "rate_of_change_per_min": round(rate_of_change, 2),
            "is_outlier": is_outlier,
            "consecutive": self.consecutive_anomalies
        }


class NodeAnomalyDetector:
    """
    Maintains anomaly tracking across all sensor channels for a specific node.
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.channels = {
            "temperature": ChannelAnomalyTracker("temperature", alpha=0.2),
            "water_level": ChannelAnomalyTracker("water_level", alpha=0.3),
            "mq2_smoke": ChannelAnomalyTracker("mq2_smoke", alpha=0.15),
            "mq7_co": ChannelAnomalyTracker("mq7_co", alpha=0.15),
            "gas_res": ChannelAnomalyTracker("gas_res", alpha=0.2),
            "rain": ChannelAnomalyTracker("rain", alpha=0.25)
        }

    def process(self, norm_data: Dict[str, Any], timestamp: float) -> Dict[str, Any]:
        results = {}
        results["temperature"] = self.channels["temperature"].update(norm_data["temperature_c"], timestamp)
        results["water_level"] = self.channels["water_level"].update(norm_data["water_level_cm"], timestamp)
        results["mq2_smoke"] = self.channels["mq2_smoke"].update(norm_data["mq2_anomaly_pct"], timestamp)
        results["mq7_co"] = self.channels["mq7_co"].update(norm_data["mq7_anomaly_pct"], timestamp)
        results["gas_res"] = self.channels["gas_res"].update(norm_data["gas_resistance_ohms"], timestamp)
        results["rain"] = self.channels["rain"].update(norm_data["rain_intensity_pct"], timestamp)
        return results
