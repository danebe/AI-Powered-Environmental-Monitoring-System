"""
Environmental Intelligence Network
Sensor Normalization and Quality Validation Layer
"""

from typing import Dict, Any, Tuple
import math
from ..schemas import TelemetryPayload, SensorHealth


class SensorNormalizer:
    """
    Transforms raw ADC values and uncalibrated metrics into normalized,
    physically bounded indicators while checking quality bounds.
    """

    TEMP_MIN_C         = -40.0
    TEMP_MAX_C         = 85.0
    HUMIDITY_MIN_PCT   = 0.0
    HUMIDITY_MAX_PCT   = 100.0
    PRESSURE_MIN_HPA   = 800.0
    PRESSURE_MAX_HPA   = 1200.0
    WATER_LEVEL_MAX_CM = 200.0

    @staticmethod
    def normalize_rain(rain_raw: int) -> Tuple[float, str]:
        """FC-37: ADC 4095 = dry (0 %), ADC <= 600 = torrential (100 %)."""
        if rain_raw < 0 or rain_raw > 4095:
            return 0.0, "INVALID"
        clamped = max(600, min(4095, rain_raw))
        intensity = ((4095.0 - clamped) / (4095.0 - 600.0)) * 100.0
        health = "ONLINE" if rain_raw > 50 else "DEGRADED"
        return round(max(0.0, min(100.0, intensity)), 1), health

    @staticmethod
    def normalize_gas_mq2(mq2_raw: int, baseline: float = 300.0) -> Tuple[float, str]:
        """MQ-2: anomaly percentage relative to clean-air baseline."""
        if mq2_raw < 0 or mq2_raw > 4095:
            return 0.0, "INVALID"
        diff = max(0.0, mq2_raw - baseline)
        pct = min(100.0, (diff / 2500.0) * 100.0)
        health = "ONLINE" if mq2_raw > 15 else "DEGRADED"
        return round(pct, 1), health

    @staticmethod
    def normalize_gas_mq7(mq7_raw: int, baseline: float = 250.0) -> Tuple[float, str]:
        """MQ-7 CO: anomaly percentage relative to baseline."""
        if mq7_raw < 0 or mq7_raw > 4095:
            return 0.0, "INVALID"
        diff = max(0.0, mq7_raw - baseline)
        pct = min(100.0, (diff / 2200.0) * 100.0)
        health = "ONLINE" if mq7_raw > 15 else "DEGRADED"
        return round(pct, 1), health

    @staticmethod
    def normalize_soil_moisture(soil_raw: int,
                                dry_adc: int = 3500,
                                wet_adc: int = 800) -> Tuple[float, str]:
        """
        FC-28 resistive probe — lower ADC = wetter (inverted scale).
        dry_adc: raw reading in dry air
        wet_adc: raw reading fully submerged
        Returns (moisture_pct 0–100, health_str).
        """
        if soil_raw < 0 or soil_raw > 4095:
            return 0.0, "INVALID"
        if soil_raw < 10 or soil_raw > 4090:
            return 0.0, "DEGRADED"
        rng = float(dry_adc - wet_adc)
        offset = float(dry_adc - soil_raw)
        pct = max(0.0, min(100.0, (offset / rng) * 100.0))
        return round(pct, 1), "ONLINE"

    @staticmethod
    def normalize_water_quality(ph: float, turbidity_ntu: float) -> Tuple[float, str]:
        """
        Combined water degradation index (0–100).
        pH deviation from neutral 7.0 + turbidity.
        """
        if math.isnan(ph) or math.isnan(turbidity_ntu):
            return 0.0, "INVALID"
        # pH: max deviation of 3.0 maps to 50 pts
        ph_dev = abs(ph - 7.0)
        ph_pts = min(50.0, (ph_dev / 3.0) * 50.0)
        # Turbidity: 200 NTU = 50 pts
        turb_pts = min(50.0, (turbidity_ntu / 200.0) * 50.0)
        index = min(100.0, ph_pts + turb_pts)
        return round(index, 1), "ONLINE"

    @classmethod
    def sanitize_and_normalize(cls, payload: TelemetryPayload) -> Dict[str, Any]:
        """
        Sanitizes raw incoming payload, replaces NaN/Inf with fallback values,
        and computes all normalized indicators.
        """
        # Temperature
        temp = payload.temperature
        temp_health = payload.sensor_health.bme680
        if math.isnan(temp) or math.isinf(temp) or not (cls.TEMP_MIN_C <= temp <= cls.TEMP_MAX_C):
            temp, temp_health = 25.0, "INVALID"

        # Humidity
        hum = payload.humidity
        if math.isnan(hum) or math.isinf(hum) or not (cls.HUMIDITY_MIN_PCT <= hum <= cls.HUMIDITY_MAX_PCT):
            hum, temp_health = 50.0, "INVALID"

        # Pressure
        pres = payload.pressure
        if math.isnan(pres) or math.isinf(pres) or not (cls.PRESSURE_MIN_HPA <= pres <= cls.PRESSURE_MAX_HPA):
            pres = 1013.25

        # Water level
        wl = payload.water_level_cm
        wl_health = payload.sensor_health.ultrasonic
        if math.isnan(wl) or math.isinf(wl) or not (0.0 <= wl <= cls.WATER_LEVEL_MAX_CM):
            wl, wl_health = 0.0, "INVALID"

        # Water quality
        ph       = payload.water_ph          if not math.isnan(payload.water_ph)           else 7.0
        turb_ntu = payload.water_turbidity_ntu if not math.isnan(payload.water_turbidity_ntu) else 0.0
        ph = max(0.0, min(14.0, ph))
        turb_ntu = max(0.0, turb_ntu)

        # Normalisations
        rain_pct,   rain_health   = cls.normalize_rain(payload.rain_raw)
        mq2_pct,    mq2_health    = cls.normalize_gas_mq2(payload.mq2_raw)
        mq7_pct,    mq7_health    = cls.normalize_gas_mq7(payload.mq7_raw)
        soil_pct,   soil_health   = cls.normalize_soil_moisture(payload.soil_moisture_raw)
        wq_index,   _wq_health    = cls.normalize_water_quality(ph, turb_ntu)

        return {
            "temperature_c":               round(temp, 2),
            "humidity_pct":                round(hum, 1),
            "pressure_hpa":                round(pres, 1),
            "gas_resistance_ohms":         max(0.0, payload.gas_resistance),
            "water_level_cm":              round(wl, 2),
            "water_rate_of_rise_cm_min":   round(payload.water_rate_of_rise_cm_min, 2),
            "rain_intensity_pct":          rain_pct,
            "mq2_anomaly_pct":             mq2_pct,
            "mq7_anomaly_pct":             mq7_pct,
            "soil_moisture_pct":           soil_pct,
            "vibration_hits":              max(0, payload.vibration_hits),
            "water_ph":                    round(ph, 2),
            "water_turbidity_ntu":         round(turb_ntu, 1),
            "water_quality_index":         wq_index,
            "flame_detected":              bool(payload.flame_detected),
            "signal_strength":             payload.signal_strength,
            "health_bme680":               temp_health,
            "health_ultrasonic":           wl_health,
            "health_rain":                 rain_health,
            "health_mq2":                  mq2_health,
            "health_mq7":                  mq7_health,
            "health_flame":                payload.sensor_health.flame,
            "health_soil_moisture":        soil_health,
            "health_vibration":            payload.sensor_health.vibration,
        }
