"""
Environmental Intelligence Network
Multi-Sensor Risk Fusion Engine — 7 Hazard Categories
"""

from typing import Dict, Any, List, Tuple
from ..schemas import HazardScoreBreakdown, SystemThresholds


class RiskFusionEngine:
    """
    Deterministic multi-sensor fusion across 7 hazard domains.
    Produces explainable scoring breakdowns with contributing factor weights.
    """

    def __init__(self, thresholds: SystemThresholds = None):
        self.thresholds = thresholds or SystemThresholds()

    def classify_severity(self, score: float) -> str:
        t = self.thresholds
        if score >= t.critical_min: return "CRITICAL"
        if score > t.low_max:       return "WARNING"
        if score > t.normal_max:    return "LOW"
        return "NORMAL"

    def evaluate_node(self, norm: Dict[str, Any], stats: Dict[str, Any]) -> HazardScoreBreakdown:
        bd = HazardScoreBreakdown()

        bd.flood_score,        bd.flood_severity,        bd.flood_reasons,        bd.flood_weights        = self._compute_flood_risk(norm, stats)
        bd.fire_score,         bd.fire_severity,         bd.fire_reasons,         bd.fire_weights         = self._compute_fire_risk(norm, stats)
        bd.pollution_score,    bd.pollution_severity,    bd.pollution_reasons,    bd.pollution_weights    = self._compute_pollution_risk(norm, stats)
        bd.heat_score,         bd.heat_severity,         bd.heat_reasons,         bd.heat_weights         = self._compute_heat_risk(norm, stats)
        bd.landslide_score,    bd.landslide_severity,    bd.landslide_reasons,    bd.landslide_weights    = self._compute_landslide_risk(norm, stats)
        bd.industrial_score,   bd.industrial_severity,   bd.industrial_reasons,   bd.industrial_weights   = self._compute_industrial_risk(norm, stats)
        bd.water_quality_score, bd.water_quality_severity, bd.water_quality_reasons, bd.water_quality_weights = self._compute_water_quality_risk(norm, stats)

        for attr in ("flood_score","fire_score","pollution_score","heat_score",
                     "landslide_score","industrial_score","water_quality_score"):
            setattr(bd, attr, round(getattr(bd, attr), 1))

        # Determine overall highest hazard
        candidates = [
            ("FLOOD",        bd.flood_score,         bd.flood_severity),
            ("FIRE",         bd.fire_score,          bd.fire_severity),
            ("POLLUTION",    bd.pollution_score,     bd.pollution_severity),
            ("HEAT",         bd.heat_score,          bd.heat_severity),
            ("LANDSLIDE",    bd.landslide_score,     bd.landslide_severity),
            ("INDUSTRIAL",   bd.industrial_score,    bd.industrial_severity),
            ("WATER_QUALITY",bd.water_quality_score, bd.water_quality_severity),
        ]
        best = max(candidates, key=lambda x: x[1])
        bd.highest_score    = round(best[1], 1)
        bd.highest_hazard   = best[0] if best[1] >= self.thresholds.normal_max else "NONE"
        bd.highest_severity = best[2] if best[1] >= self.thresholds.normal_max else "NORMAL"
        return bd

    # ------------------------------------------------------------------
    # 1. Flood Risk  (0–100)
    # ------------------------------------------------------------------
    def _compute_flood_risk(self, norm, stats):
        reasons, weights, total = [], {}, 0.0
        wl   = norm["water_level_cm"]
        t    = self.thresholds

        # Water depth (0–40 pts)
        if wl >= t.water_level_critical_cm:
            dp = 40.0; reasons.append(f"Water level critical ({wl:.1f} cm)")
        elif wl >= t.water_level_warning_cm:
            dp = 20.0 + ((wl - t.water_level_warning_cm) / (t.water_level_critical_cm - t.water_level_warning_cm)) * 20.0
            reasons.append(f"Water level elevated ({wl:.1f} cm)")
        elif wl > 15.0:
            dp = (wl / t.water_level_warning_cm) * 20.0
        else:
            dp = (wl / 15.0) * 8.0
        weights["water_depth"] = round(dp, 1); total += dp

        # Rate of rise (0–30 pts)
        rate = max(norm["water_rate_of_rise_cm_min"], stats["water_level"]["rate_of_change_per_min"])
        if rate >= t.water_rise_rate_critical_cm_min:
            rp = 30.0; reasons.append(f"Flash flood surge: +{rate:.1f} cm/min")
        elif rate >= t.water_rise_rate_warning_cm_min:
            rp = 15.0 + ((rate - t.water_rise_rate_warning_cm_min) / (t.water_rise_rate_critical_cm_min - t.water_rise_rate_warning_cm_min)) * 15.0
            reasons.append(f"Water rising at +{rate:.1f} cm/min")
        else:
            rp = (rate / t.water_rise_rate_warning_cm_min) * 15.0 if rate > 0.5 else 0.0
        weights["water_rate_of_rise"] = round(rp, 1); total += rp

        # Rainfall (0–20 pts)
        rain = norm["rain_intensity_pct"]
        rn_pts = (rain / 100.0) * 20.0
        if rain >= 70.0: reasons.append(f"Heavy rainfall ({rain:.0f}%)")
        elif rain >= 40.0: reasons.append(f"Moderate rainfall ({rain:.0f}%)")
        weights["rainfall_intensity"] = round(rn_pts, 1); total += rn_pts

        # Humidity saturation (0–10 pts)
        hum = norm["humidity_pct"]
        hp = 10.0 if hum >= 85.0 else (((hum - 70.0) / 15.0) * 10.0 if hum >= 70.0 else 0.0)
        weights["humidity_saturation"] = round(hp, 1); total += hp

        score = max(0.0, min(100.0, total))
        if not reasons: reasons.append("Drainage channel flow within normal capacity")
        return score, self.classify_severity(score), reasons, weights

    # ------------------------------------------------------------------
    # 2. Fire / Wildfire Risk  (0–100)
    # ------------------------------------------------------------------
    def _compute_fire_risk(self, norm, stats):
        reasons, weights, total = [], {}, 0.0

        # Optical flame (0 or 45 pts)
        fp = 45.0 if norm["flame_detected"] else 0.0
        if norm["flame_detected"]: reasons.append("Optical IR flame sensor triggered")
        weights["optical_flame"] = fp; total += fp

        # MQ-2 smoke (0–25 pts)
        mq2 = norm["mq2_anomaly_pct"]
        sp = (mq2 / 100.0) * 25.0
        if mq2 >= self.thresholds.mq2_smoke_critical_pct: reasons.append(f"Critical smoke concentration ({mq2:.0f}%)")
        elif mq2 >= self.thresholds.mq2_smoke_warning_pct: reasons.append(f"Elevated smoke ({mq2:.0f}%)")
        weights["smoke_mq2"] = round(sp, 1); total += sp

        # MQ-7 CO (0–15 pts)
        mq7 = norm["mq7_anomaly_pct"]
        cp = (mq7 / 100.0) * 15.0
        if mq7 >= self.thresholds.mq7_co_critical_pct: reasons.append(f"High CO emission ({mq7:.0f}%)")
        weights["co_mq7"] = round(cp, 1); total += cp

        # Temperature & thermal surge (0–15 pts)
        temp = norm["temperature_c"]
        tr   = stats["temperature"]["rate_of_change_per_min"]
        tp   = 0.0
        if temp >= self.thresholds.temp_critical_c:
            tp += 10.0; reasons.append(f"Extreme temperature ({temp:.1f} °C)")
        elif temp >= self.thresholds.temp_warning_c:
            tp += 5.0 + ((temp - self.thresholds.temp_warning_c) / (self.thresholds.temp_critical_c - self.thresholds.temp_warning_c)) * 5.0
        if tr >= self.thresholds.temp_rise_rate_critical_c_min:
            tp += 5.0; reasons.append(f"Rapid thermal spike (+{tr:.1f} °C/min)")
        tp = min(15.0, tp)
        weights["thermal_conditions"] = round(tp, 1); total += tp

        if not norm["flame_detected"]:
            if max(stats["mq2_smoke"]["consecutive"], stats["mq7_co"]["consecutive"]) < self.thresholds.consecutive_spikes_required and total > 35.0:
                total *= 0.65
                reasons.append("Awaiting persistence confirmation")

        score = max(0.0, min(100.0, total))
        if not reasons: reasons.append("No active combustion or thermal anomalies")
        return score, self.classify_severity(score), reasons, weights

    # ------------------------------------------------------------------
    # 3. Pollution (Air Quality) Risk  (0–100)
    # ------------------------------------------------------------------
    def _compute_pollution_risk(self, norm, stats):
        reasons, weights, total = [], {}, 0.0

        # BME680 VOC resistance (0–35 pts)
        gr = norm["gas_resistance_ohms"]
        bp = 0.0
        if norm["health_bme680"] == "ONLINE" and gr > 0:
            if gr <= self.thresholds.bme680_gas_res_critical_ohms:
                bp = 35.0; reasons.append(f"Severe air quality degradation ({gr/1000:.1f} kΩ)")
            elif gr <= self.thresholds.bme680_gas_res_warning_ohms:
                bp = 15.0 + ((self.thresholds.bme680_gas_res_warning_ohms - gr) /
                              (self.thresholds.bme680_gas_res_warning_ohms - self.thresholds.bme680_gas_res_critical_ohms)) * 20.0
                reasons.append(f"Elevated VOC index ({gr/1000:.1f} kΩ)")
            elif gr < 100000.0:
                bp = ((100000.0 - gr) / 40000.0) * 15.0
        weights["bme680_voc"] = round(bp, 1); total += bp

        # MQ-7 CO (0–35 pts)
        mq7 = norm["mq7_anomaly_pct"]
        mp7 = (mq7 / 100.0) * 35.0
        if mq7 >= self.thresholds.mq7_co_critical_pct: reasons.append(f"Hazardous CO level ({mq7:.0f}%)")
        elif mq7 >= self.thresholds.mq7_co_warning_pct: reasons.append(f"Elevated CO ({mq7:.0f}%)")
        weights["co_mq7"] = round(mp7, 1); total += mp7

        # MQ-2 (0–30 pts)
        mq2 = norm["mq2_anomaly_pct"]
        mp2 = (mq2 / 100.0) * 30.0
        if mq2 >= self.thresholds.mq2_smoke_critical_pct: reasons.append(f"Persistent gas/solvent vapor ({mq2:.0f}%)")
        weights["gas_mq2"] = round(mp2, 1); total += mp2

        if max(stats["gas_res"]["consecutive"], stats["mq7_co"]["consecutive"]) < self.thresholds.consecutive_spikes_required and total > 40.0:
            total *= 0.7
            reasons.append("Single-sample transient air disturbance filtered")

        score = max(0.0, min(100.0, total))
        if not reasons: reasons.append("Air quality within clean baseline")
        return score, self.classify_severity(score), reasons, weights

    # ------------------------------------------------------------------
    # 4. Extreme Heat Risk  (0–100)
    # ------------------------------------------------------------------
    def _compute_heat_risk(self, norm, stats):
        reasons, weights, total = [], {}, 0.0
        temp = norm["temperature_c"]
        hum  = norm["humidity_pct"]
        t    = self.thresholds

        # Temperature level (0–40 pts)
        if temp >= t.temp_heat_critical_c:
            tp = 40.0; reasons.append(f"Extreme heat: {temp:.1f} °C")
        elif temp >= t.temp_heat_warning_c:
            tp = ((temp - t.temp_heat_warning_c) / (t.temp_heat_critical_c - t.temp_heat_warning_c)) * 40.0
            reasons.append(f"High temperature: {temp:.1f} °C")
        else:
            tp = 0.0
        weights["temperature"] = round(tp, 1); total += tp

        # Humidity amplification (0–20 pts) — high RH worsens heat stress
        if tp > 0 and hum >= 70.0:
            ha = ((hum - 70.0) / 30.0) * 20.0
            if ha > 5.0: reasons.append(f"High humidity amplifying heat index ({hum:.0f}% RH)")
        else:
            ha = 0.0
        weights["humidity_amplification"] = round(ha, 1); total += ha

        # Low humidity dry-heat amplification (0–20 pts) — fire-weather risk
        if tp > 10.0 and hum < 20.0:
            da = (1.0 - hum / 20.0) * 20.0
            reasons.append(f"Extreme dry heat conditions ({hum:.0f}% RH)")
        else:
            da = 0.0
        weights["dry_heat"] = round(da, 1); total += da

        # Sustained heat: EMA baseline well above normal (0–20 pts)
        ema_temp = stats["temperature"]["ema"]
        if ema_temp >= t.temp_heat_warning_c and tp > 0:
            sa = min(20.0, ((ema_temp - t.temp_heat_warning_c) / 10.0) * 20.0)
            reasons.append(f"Sustained elevated temperature (EMA {ema_temp:.1f} °C)")
        else:
            sa = 0.0
        weights["sustained_heat"] = round(sa, 1); total += sa

        score = max(0.0, min(100.0, total))
        if not reasons: reasons.append("Temperature within normal operating range")
        return score, self.classify_severity(score), reasons, weights

    # ------------------------------------------------------------------
    # 5. Landslide Precursor Risk  (0–100)
    # ------------------------------------------------------------------
    def _compute_landslide_risk(self, norm, stats):
        reasons, weights, total = [], {}, 0.0
        soil = norm["soil_moisture_pct"]
        vib  = norm["vibration_hits"]
        rain = norm["rain_intensity_pct"]
        t    = self.thresholds

        # Soil saturation (0–40 pts)
        if soil >= t.soil_moisture_critical_pct:
            sp = 40.0; reasons.append(f"Critical soil saturation ({soil:.0f}%)")
        elif soil >= t.soil_moisture_warning_pct:
            sp = ((soil - t.soil_moisture_warning_pct) / (t.soil_moisture_critical_pct - t.soil_moisture_warning_pct)) * 40.0
            reasons.append(f"Elevated soil moisture ({soil:.0f}%)")
        elif soil > 40.0:
            sp = (soil / t.soil_moisture_warning_pct) * 15.0
        else:
            sp = 0.0
        weights["soil_saturation"] = round(sp, 1); total += sp

        # Vibration burst (0–35 pts)
        if vib >= t.vibration_critical_hits:
            vp = 35.0; reasons.append(f"Critical ground vibration ({vib} hits/s)")
        elif vib >= t.vibration_warning_hits:
            vp = ((vib - t.vibration_warning_hits) / (t.vibration_critical_hits - t.vibration_warning_hits)) * 35.0
            reasons.append(f"Ground vibration detected ({vib} hits/s)")
        else:
            vp = 0.0
        weights["vibration"] = round(vp, 1); total += vp

        # Rain + saturation correlation (0–25 pts)
        if rain > 40.0 and soil > 50.0:
            rp = (rain / 100.0) * 25.0
            if rp > 8.0: reasons.append(f"Heavy rainfall on saturated ground ({rain:.0f}%)")
        else:
            rp = 0.0
        weights["rain_correlation"] = round(rp, 1); total += rp

        # Persistence filter — require 3+ consecutive readings before scoring > 50
        consec = stats["soil_moisture"]["consecutive"]
        if consec < t.consecutive_spikes_required and total > 50.0:
            total = min(total, 50.0)
            reasons.append("Monitoring — awaiting persistent confirmation")

        score = max(0.0, min(100.0, total))
        if not reasons: reasons.append("Ground conditions stable")
        return score, self.classify_severity(score), reasons, weights

    # ------------------------------------------------------------------
    # 6. Industrial Emissions Risk  (0–100)
    # Chemical-leak-tuned variant — lower thresholds, sustained focus
    # ------------------------------------------------------------------
    def _compute_industrial_risk(self, norm, stats):
        reasons, weights, total = [], {}, 0.0

        # MQ-2 chemical/combustible index (0–35 pts) — lower threshold than fire model
        mq2 = norm["mq2_anomaly_pct"]
        m2p = (mq2 / 100.0) * 35.0
        if mq2 >= 60.0: reasons.append(f"Elevated combustible chemical vapors ({mq2:.0f}%)")
        elif mq2 >= 30.0: reasons.append(f"Trace chemical gas detected ({mq2:.0f}%)")
        weights["mq2_chemical"] = round(m2p, 1); total += m2p

        # MQ-7 CO persistent industrial index (0–35 pts)
        mq7 = norm["mq7_anomaly_pct"]
        m7p = (mq7 / 100.0) * 35.0
        if mq7 >= 50.0: reasons.append(f"Industrial CO emission ({mq7:.0f}%)")
        elif mq7 >= 25.0: reasons.append(f"Moderate CO detected ({mq7:.0f}%)")
        weights["mq7_co_industrial"] = round(m7p, 1); total += m7p

        # BME680 VOC from chemical processes (0–30 pts)
        gr = norm["gas_resistance_ohms"]
        bp = 0.0
        if norm["health_bme680"] == "ONLINE" and gr > 0:
            if gr <= 25000.0:
                bp = 30.0; reasons.append(f"Severe VOC chemical load ({gr/1000:.1f} kΩ)")
            elif gr <= 80000.0:
                bp = ((80000.0 - gr) / 55000.0) * 30.0
                if bp > 10.0: reasons.append(f"VOC concentration elevated ({gr/1000:.1f} kΩ)")
        weights["voc_chemical"] = round(bp, 1); total += bp

        # Persistence filter — industrial leaks tend to persist; single spikes less reliable
        consec = max(stats["mq2_smoke"]["consecutive"], stats["mq7_co"]["consecutive"])
        if consec < self.thresholds.consecutive_spikes_required and total > 35.0:
            total *= 0.7
            reasons.append("Single-reading chemical spike — monitoring")

        score = max(0.0, min(100.0, total))
        if not reasons: reasons.append("Industrial emission sensors within safe baseline")
        return score, self.classify_severity(score), reasons, weights

    # ------------------------------------------------------------------
    # 7. Water Quality Risk  (0–100)
    # ------------------------------------------------------------------
    def _compute_water_quality_risk(self, norm, stats):
        reasons, weights, total = [], {}, 0.0
        ph   = norm["water_ph"]
        turb = norm["water_turbidity_ntu"]
        wl   = norm["water_level_cm"]
        t    = self.thresholds

        # pH deviation from neutral (0–40 pts)
        ph_dev = abs(ph - 7.0)
        if ph_dev >= t.water_ph_critical_deviation:
            pp = 40.0
            reasons.append(f"Critical pH deviation: {ph:.1f} (neutral is 7.0)")
        elif ph_dev >= t.water_ph_warning_deviation:
            pp = ((ph_dev - t.water_ph_warning_deviation) /
                  (t.water_ph_critical_deviation - t.water_ph_warning_deviation)) * 40.0
            reasons.append(f"Water pH outside normal range ({ph:.1f})")
        else:
            pp = (ph_dev / t.water_ph_warning_deviation) * 15.0 if ph_dev > 0.5 else 0.0
        weights["ph_deviation"] = round(pp, 1); total += pp

        # Turbidity (0–35 pts)
        if turb >= t.water_turbidity_critical_ntu:
            tp = 35.0; reasons.append(f"High turbidity: {turb:.0f} NTU")
        elif turb >= t.water_turbidity_warning_ntu:
            tp = ((turb - t.water_turbidity_warning_ntu) /
                  (t.water_turbidity_critical_ntu - t.water_turbidity_warning_ntu)) * 35.0
            reasons.append(f"Elevated turbidity: {turb:.0f} NTU")
        else:
            tp = (turb / t.water_turbidity_warning_ntu) * 10.0 if turb > 5.0 else 0.0
        weights["turbidity"] = round(tp, 1); total += tp

        # Flood-turbidity correlation (0–25 pts) — rising water + turbidity = contamination
        if wl > 20.0 and turb > 30.0:
            fl = min(25.0, (wl / 65.0) * (turb / 200.0) * 25.0)
            if fl > 5.0: reasons.append("Flood-contamination correlation: turbid floodwater rising")
        else:
            fl = 0.0
        weights["flood_turbidity_corr"] = round(fl, 1); total += fl

        score = max(0.0, min(100.0, total))
        if not reasons: reasons.append("Water quality parameters within safe limits")
        return score, self.classify_severity(score), reasons, weights
