"""
SIH 2026 Environmental Monitoring Network
Sensor Normalization and Quality Validation Layer
"""

from typing import Dict, Any, Tuple
import math
from ..schemas import TelemetryPayload, SensorHealth


class SensorNormalizer:
    """
    Transforms raw ADC, raw voltages, and uncalibrated metrics into normalized,
    physically bounded indicators while checking quality bounds.
    """

    # Physical valid bounds
    TEMP_MIN_C = -40.0
    TEMP_MAX_C = 85.0

    HUMIDITY_MIN_PCT = 0.0
    HUMIDITY_MAX_PCT = 100.0

    PRESSURE_MIN_HPA = 800.0
    PRESSURE_MAX_HPA = 1200.0

    WATER_LEVEL_MAX_CM = 200.0

    @staticmethod
    def normalize_rain(rain_raw: int) -> Tuple[float, str]:
        """
        FC-37 Rain Sensor:
        ADC = 4095 (Dry) -> 0%
        ADC <= 800 (Torrential rain) -> 100%
        """
        if rain_raw < 0 or rain_raw > 4095:
            return 0.0, "INVALID"

        # Invert scale: lower resistance / lower ADC means wetter
        clamped_raw = max(600, min(4095, rain_raw))
        # Linear/exponential interpolation
        intensity = ((4095.0 - clamped_raw) / (4095.0 - 600.0)) * 100.0
        intensity = max(0.0, min(100.0, intensity))

        health = "ONLINE" if rain_raw > 50 else "DEGRADED"
        return round(intensity, 1), health

    @staticmethod
    def normalize_gas_mq2(mq2_raw: int, baseline: float = 300.0) -> Tuple[float, str]:
        """
        MQ-2 Smoke & Combustible Gas:
        Computes normalized anomaly percentage relative to baseline.
        """
        if mq2_raw < 0 or mq2_raw > 4095:
            return 0.0, "INVALID"

        diff = max(0.0, mq2_raw - baseline)
        anomaly_pct = min(100.0, (diff / 2500.0) * 100.0)

        health = "ONLINE" if mq2_raw > 15 else "DEGRADED"
        return round(anomaly_pct, 1), health

    @staticmethod
    def normalize_gas_mq7(mq7_raw: int, baseline: float = 250.0) -> Tuple[float, str]:
        """
        MQ-7 Carbon Monoxide:
        Computes normalized anomaly percentage relative to baseline.
        """
        if mq7_raw < 0 or mq7_raw > 4095:
            return 0.0, "INVALID"

        diff = max(0.0, mq7_raw - baseline)
        anomaly_pct = min(100.0, (diff / 2200.0) * 100.0)

        health = "ONLINE" if mq7_raw > 15 else "DEGRADED"
        return round(anomaly_pct, 1), health

    @classmethod
    def sanitize_and_normalize(cls, payload: TelemetryPayload) -> Dict[str, Any]:
        """
        Sanitizes raw incoming payload, replaces NaNs/Infs with fallback safe bounds,
        and computes normalized indicators.
        """
        # 1. Temperature sanity
        temp = payload.temperature
        temp_health = payload.sensor_health.bme680
        if math.isnan(temp) or math.isinf(temp) or temp < cls.TEMP_MIN_C or temp > cls.TEMP_MAX_C:
            temp = 25.0
            temp_health = "INVALID"

        # 2. Humidity sanity
        hum = payload.humidity
        if math.isnan(hum) or math.isinf(hum) or hum < cls.HUMIDITY_MIN_PCT or hum > cls.HUMIDITY_MAX_PCT:
            hum = 50.0
            temp_health = "INVALID"

        # 3. Pressure sanity
        pres = payload.pressure
        if math.isnan(pres) or math.isinf(pres) or pres < cls.PRESSURE_MIN_HPA or pres > cls.PRESSURE_MAX_HPA:
            pres = 1013.25

        # 4. Water level sanity
        wl = payload.water_level_cm
        wl_health = payload.sensor_health.ultrasonic
        if math.isnan(wl) or math.isinf(wl) or wl < 0.0 or wl > cls.WATER_LEVEL_MAX_CM:
            wl = 0.0
            wl_health = "INVALID"

        # 5. Normalizations
        rain_pct, rain_health = cls.normalize_rain(payload.rain_raw)
        mq2_pct, mq2_health = cls.normalize_gas_mq2(payload.mq2_raw)
        mq7_pct, mq7_health = cls.normalize_gas_mq7(payload.mq7_raw)

        return {
            "temperature_c": round(temp, 2),
            "humidity_pct": round(hum, 1),
            "pressure_hpa": round(pres, 1),
            "gas_resistance_ohms": max(0.0, payload.gas_resistance),
            "water_level_cm": round(wl, 2),
            "water_rate_of_rise_cm_min": round(payload.water_rate_of_rise_cm_min, 2),
            "rain_intensity_pct": rain_pct,
            "mq2_anomaly_pct": mq2_pct,
            "mq7_anomaly_pct": mq7_pct,
            "flame_detected": bool(payload.flame_detected),
            "battery_voltage": round(payload.battery_voltage, 2),
            "signal_strength": payload.signal_strength,
            "health_bme680": temp_health,
            "health_ultrasonic": wl_health,
            "health_rain": rain_health,
            "health_mq2": mq2_health,
            "health_mq7": mq7_health,
            "health_flame": payload.sensor_health.flame,
        }
