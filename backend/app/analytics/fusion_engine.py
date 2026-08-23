"""
SIH 2026 Environmental Monitoring Network
Multi-Sensor Risk Fusion Engine with Transparent Factor Weighting & Explainability
"""

from typing import Dict, Any, List, Tuple
from ..schemas import HazardScoreBreakdown, SystemThresholds


class RiskFusionEngine:
    """
    Executes deterministic multi-sensor fusion across Flood, Fire, and Pollution domains.
    Generates explainable scoring breakdowns showing exact contributing factors and reasons.
    """

    def __init__(self, thresholds: SystemThresholds = None):
        self.thresholds = thresholds or SystemThresholds()

    def classify_severity(self, score: float) -> str:
        if score >= self.thresholds.critical_min:
            return "CRITICAL"
        elif score > self.thresholds.low_max:
            return "WARNING"
        elif score > self.thresholds.normal_max:
            return "LOW"
        else:
            return "NORMAL"

    def evaluate_node(self, norm_data: Dict[str, Any], anomaly_stats: Dict[str, Any]) -> HazardScoreBreakdown:
        breakdown = HazardScoreBreakdown()

        # 1. Flood Risk Fusion
        f_score, f_sev, f_reasons, f_weights = self._compute_flood_risk(norm_data, anomaly_stats)
        breakdown.flood_score = round(f_score, 1)
        breakdown.flood_severity = f_sev
        breakdown.flood_reasons = f_reasons
        breakdown.flood_weights = f_weights

        # 2. Fire Risk Fusion
        fire_score, fire_sev, fire_reasons, fire_weights = self._compute_fire_risk(norm_data, anomaly_stats)
        breakdown.fire_score = round(fire_score, 1)
        breakdown.fire_severity = fire_sev
        breakdown.fire_reasons = fire_reasons
        breakdown.fire_weights = fire_weights

        # 3. Pollution Risk Fusion
        p_score, p_sev, p_reasons, p_weights = self._compute_pollution_risk(norm_data, anomaly_stats)
        breakdown.pollution_score = round(p_score, 1)
        breakdown.pollution_severity = p_sev
        breakdown.pollution_reasons = p_reasons
        breakdown.pollution_weights = p_weights

        # 4. Highest Overall Hazard Classification
        max_score = f_score
        max_hazard = "FLOOD"
        max_sev = f_sev

        if fire_score > max_score:
            max_score = fire_score
            max_hazard = "FIRE"
            max_sev = fire_sev

        if p_score > max_score:
            max_score = p_score
            max_hazard = "POLLUTION"
            max_sev = p_sev

        if max_score < self.thresholds.normal_max:
            max_hazard = "NONE"
            max_sev = "NORMAL"

        breakdown.highest_score = round(max_score, 1)
        breakdown.highest_hazard = max_hazard
        breakdown.highest_severity = max_sev

        return breakdown

    def _compute_flood_risk(self, norm: Dict[str, Any], stats: Dict[str, Any]) -> Tuple[float, str, List[str], Dict[str, float]]:
        """
        Flood Risk Model (0-100):
        Factors:
        - Water Level Depth (0-40 pts)
        - Water Rate of Rise (0-30 pts)
        - Rain Intensity (0-20 pts)
        - Conductive Water Level / Humidity proxy (0-10 pts)
        """
        reasons = []
        weights = {}
        total = 0.0

        wl = norm["water_level_cm"]
        # 1. Depth Contribution (0-40)
        if wl >= self.thresholds.water_level_critical_cm:
            depth_pts = 40.0
            reasons.append(f"Water level critical ({wl:.1f} cm >= {self.thresholds.water_level_critical_cm} cm)")
        elif wl >= self.thresholds.water_level_warning_cm:
            ratio = (wl - self.thresholds.water_level_warning_cm) / (self.thresholds.water_level_critical_cm - self.thresholds.water_level_warning_cm)
            depth_pts = 20.0 + (ratio * 20.0)
            reasons.append(f"Water level elevated ({wl:.1f} cm, warning threshold exceeded)")
        elif wl > 15.0:
            depth_pts = (wl / self.thresholds.water_level_warning_cm) * 20.0
        else:
            depth_pts = (wl / 15.0) * 8.0
        weights["water_depth"] = round(depth_pts, 1)
        total += depth_pts

        # 2. Rate of Rise Contribution (0-30)
        # Check both direct payload rate and anomaly derivative
        rate = max(norm["water_rate_of_rise_cm_min"], stats["water_level"]["rate_of_change_per_min"])
        if rate >= self.thresholds.water_rise_rate_critical_cm_min:
            rate_pts = 30.0
            reasons.append(f"Flash flood water surge: rising rapidly at +{rate:.1f} cm/min")
        elif rate >= self.thresholds.water_rise_rate_warning_cm_min:
            rate_pts = 15.0 + ((rate - self.thresholds.water_rise_rate_warning_cm_min) / (self.thresholds.water_rise_rate_critical_cm_min - self.thresholds.water_rise_rate_warning_cm_min)) * 15.0
            reasons.append(f"Water depth increasing at +{rate:.1f} cm/min")
        elif rate > 0.5:
            rate_pts = (rate / self.thresholds.water_rise_rate_warning_cm_min) * 15.0
        else:
            rate_pts = 0.0
        weights["water_rate_of_rise"] = round(rate_pts, 1)
        total += rate_pts

        # 3. Rain Intensity Contribution (0-20)
        rain_pct = norm["rain_intensity_pct"]
        rain_pts = (rain_pct / 100.0) * 20.0
        if rain_pct >= 70.0:
            reasons.append(f"Heavy rainfall detected ({rain_pct:.0f}% intensity)")
        elif rain_pct >= 40.0:
            reasons.append(f"Moderate rainfall ({rain_pct:.0f}% intensity)")
        weights["rainfall_intensity"] = round(rain_pts, 1)
        total += rain_pts

        # 4. Atmospheric / Humidity Factor (0-10)
        hum = norm["humidity_pct"]
        hum_pts = 0.0
        if hum >= 85.0:
            hum_pts = 10.0
        elif hum >= 70.0:
            hum_pts = ((hum - 70.0) / 15.0) * 10.0
        weights["humidity_saturation"] = round(hum_pts, 1)
        total += hum_pts

        final_score = max(0.0, min(100.0, total))
        severity = self.classify_severity(final_score)

        if not reasons:
            reasons.append("Normal hydrological parameters, channel flow stable")

        return final_score, severity, reasons, weights

    def _compute_fire_risk(self, norm: Dict[str, Any], stats: Dict[str, Any]) -> Tuple[float, str, List[str], Dict[str, float]]:
        """
        Fire Risk Model (0-100):
        Factors:
        - Optical Flame Sensor (0 or 45 pts)
        - MQ-2 Smoke Anomaly (0-25 pts)
        - MQ-7 CO Combustion (0-15 pts)
        - Extreme Temperature / Rate of Rise (0-15 pts)
        """
        reasons = []
        weights = {}
        total = 0.0

        # 1. Optical Flame Detection (0 or 45)
        if norm["flame_detected"]:
            flame_pts = 45.0
            reasons.append("Direct IR optical flame detected by optical sensor")
        else:
            flame_pts = 0.0
        weights["optical_flame"] = flame_pts
        total += flame_pts

        # 2. MQ-2 Smoke Anomaly (0-25)
        mq2_pct = norm["mq2_anomaly_pct"]
        smoke_pts = (mq2_pct / 100.0) * 25.0
        if mq2_pct >= self.thresholds.mq2_smoke_critical_pct:
            reasons.append(f"Critical smoke/combustion gas concentration ({mq2_pct:.0f}%)")
        elif mq2_pct >= self.thresholds.mq2_smoke_warning_pct:
            reasons.append(f"Elevated smoke anomaly ({mq2_pct:.0f}%)")
        weights["smoke_mq2"] = round(smoke_pts, 1)
        total += smoke_pts

        # 3. MQ-7 CO Anomaly (0-15)
        mq7_pct = norm["mq7_anomaly_pct"]
        co_pts = (mq7_pct / 100.0) * 15.0
        if mq7_pct >= self.thresholds.mq7_co_critical_pct:
            reasons.append(f"High carbon monoxide (CO) emission ({mq7_pct:.0f}%)")
        elif mq7_pct >= self.thresholds.mq7_co_warning_pct:
            reasons.append(f"CO anomaly present ({mq7_pct:.0f}%)")
        weights["co_mq7"] = round(co_pts, 1)
        total += co_pts

        # 4. Temperature & Thermal Surge (0-15)
        temp = norm["temperature_c"]
        temp_rate = stats["temperature"]["rate_of_change_per_min"]
        temp_pts = 0.0

        if temp >= self.thresholds.temp_critical_c:
            temp_pts += 10.0
            reasons.append(f"Extreme ambient temperature ({temp:.1f} °C)")
        elif temp >= self.thresholds.temp_warning_c:
            temp_pts += 5.0 + ((temp - self.thresholds.temp_warning_c) / (self.thresholds.temp_critical_c - self.thresholds.temp_warning_c)) * 5.0

        if temp_rate >= self.thresholds.temp_rise_rate_critical_c_min:
            temp_pts += 5.0
            reasons.append(f"Rapid thermal spike (+{temp_rate:.1f} °C/min)")

        temp_pts = min(15.0, temp_pts)
        weights["thermal_conditions"] = round(temp_pts, 1)
        total += temp_pts

        # Persistence check for non-flame combustion readings
        if not norm["flame_detected"]:
            smoke_consec = stats["mq2_smoke"]["consecutive"]
            co_consec = stats["mq7_co"]["consecutive"]
            if max(smoke_consec, co_consec) < self.thresholds.consecutive_spikes_required and total > 35.0:
                total *= 0.65  # Dampen unconfirmed transient spikes
                reasons.append("Awaiting multi-reading persistence confirmation")

        final_score = max(0.0, min(100.0, total))
        severity = self.classify_severity(final_score)

        if not reasons:
            reasons.append("No active combustion or thermal anomalies detected")

        return final_score, severity, reasons, weights

    def _compute_pollution_risk(self, norm: Dict[str, Any], stats: Dict[str, Any]) -> Tuple[float, str, List[str], Dict[str, float]]:
        """
        Pollution Risk Model (0-100):
        Factors:
        - BME680 VOC / Gas Resistance Drop (0-35 pts)
        - MQ-7 CO Persistent Index (0-35 pts)
        - MQ-2 Persistent Gas Index (0-30 pts)
        """
        reasons = []
        weights = {}
        total = 0.0

        # 1. BME680 Gas Resistance (0-35)
        gas_res = norm["gas_resistance_ohms"]
        bme_pts = 0.0
        if norm["health_bme680"] == "ONLINE" and gas_res > 0:
            if gas_res <= self.thresholds.bme680_gas_res_critical_ohms:
                bme_pts = 35.0
                reasons.append(f"Severe VOC/Air quality degradation (Resistance {gas_res/1000.0:.1f} kΩ)")
            elif gas_res <= self.thresholds.bme680_gas_res_warning_ohms:
                bme_pts = 15.0 + ((self.thresholds.bme680_gas_res_warning_ohms - gas_res) / (self.thresholds.bme680_gas_res_warning_ohms - self.thresholds.bme680_gas_res_critical_ohms)) * 20.0
                reasons.append(f"Elevated volatile organic compounds (VOC) ({gas_res/1000.0:.1f} kΩ)")
            elif gas_res < 100000.0:
                bme_pts = ((100000.0 - gas_res) / 40000.0) * 15.0
        weights["bme680_voc"] = round(bme_pts, 1)
        total += bme_pts

        # 2. MQ-7 Persistent Carbon Monoxide (0-35)
        mq7_pct = norm["mq7_anomaly_pct"]
        mq7_pts = (mq7_pct / 100.0) * 35.0
        if mq7_pct >= self.thresholds.mq7_co_critical_pct:
            reasons.append(f"Hazardous CO concentration index ({mq7_pct:.0f}%)")
        elif mq7_pct >= self.thresholds.mq7_co_warning_pct:
            reasons.append(f"Moderate CO concentration ({mq7_pct:.0f}%)")
        weights["co_mq7"] = round(mq7_pts, 1)
        total += mq7_pts

        # 3. MQ-2 Combustible / Solvent Index (0-30)
        mq2_pct = norm["mq2_anomaly_pct"]
        mq2_pts = (mq2_pct / 100.0) * 30.0
        if mq2_pct >= self.thresholds.mq2_smoke_critical_pct:
            reasons.append(f"Persistent chemical/solvent vapor detected ({mq2_pct:.0f}%)")
        weights["gas_mq2"] = round(mq2_pts, 1)
        total += mq2_pts

        # Persistence check
        gas_consec = max(stats["gas_res"]["consecutive"], stats["mq7_co"]["consecutive"])
        if gas_consec < self.thresholds.consecutive_spikes_required and total > 40.0:
            total *= 0.7
            reasons.append("Filtering single-sample transient air disturbance")

        final_score = max(0.0, min(100.0, total))
        severity = self.classify_severity(final_score)

        if not reasons:
            reasons.append("Air quality indices within clean baseline limits")

        return final_score, severity, reasons, weights
