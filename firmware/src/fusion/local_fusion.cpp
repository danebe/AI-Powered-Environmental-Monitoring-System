#include "local_fusion.h"
#include <stdio.h>
#include <string.h>

LocalFusionEngine::LocalFusionEngine()
    : _consecutive_fire_spikes(0)
    , _consecutive_pollution_spikes(0)
    , _consecutive_landslide_spikes(0)
{}

HazardSeverity LocalFusionEngine::scoreToSeverity(float score) {
    if (score >= THRESHOLD_CRITICAL_MIN) return HazardSeverity::CRITICAL;
    if (score >= 50.0f)                  return HazardSeverity::WARNING;
    if (score >= 25.0f)                  return HazardSeverity::LOW;
    return HazardSeverity::NORMAL;
}

HazardScores LocalFusionEngine::evaluate(const SensorReadings& r) {
    HazardScores scores;
    char flood_r[64]={0}, fire_r[64]={0}, poll_r[64]={0};
    char heat_r[64]={0}, land_r[64]={0};

    scores.flood_score        = computeFloodRisk(r,       flood_r, sizeof(flood_r));
    scores.fire_score         = computeFireRisk(r,        fire_r,  sizeof(fire_r));
    scores.pollution_score    = computePollutionRisk(r,   poll_r,  sizeof(poll_r));
    scores.heat_score         = computeHeatRisk(r,        heat_r,  sizeof(heat_r));
    scores.landslide_score    = computeLandslideRisk(r,   land_r,  sizeof(land_r));
    // industrial and water_quality use same sensors as pollution/flood — computed server-side
    // on-device approximation: reuse pollution score for industrial
    scores.industrial_score   = scores.pollution_score;
    scores.water_quality_score = 0.0f; // requires optional pH/turbidity probes

    scores.flood_severity        = scoreToSeverity(scores.flood_score);
    scores.fire_severity         = scoreToSeverity(scores.fire_score);
    scores.pollution_severity    = scoreToSeverity(scores.pollution_score);
    scores.heat_severity         = scoreToSeverity(scores.heat_score);
    scores.landslide_severity    = scoreToSeverity(scores.landslide_score);
    scores.industrial_severity   = scoreToSeverity(scores.industrial_score);
    scores.water_quality_severity = HazardSeverity::NORMAL;

    // Determine dominant hazard for OLED display
    float max_score = 0.0f;
    const char* max_title  = "ENV NORMAL";
    const char* max_detail = "All sensor channels nominal";

    struct { float s; const char* t; const char* d; } hazards[] = {
        { scores.flood_score,     "FLOOD",     flood_r },
        { scores.fire_score,      "FIRE",      fire_r  },
        { scores.pollution_score, "POLLUTION", poll_r  },
        { scores.heat_score,      "HEAT",      heat_r  },
        { scores.landslide_score, "LANDSLIDE", land_r  },
    };

    for (auto& h : hazards) {
        if (h.s > max_score) { max_score = h.s; max_title = h.t; max_detail = h.d; }
    }

    scores.highest_severity = scoreToSeverity(max_score);
    snprintf(scores.primary_alert_title,  sizeof(scores.primary_alert_title),
             "%s: %s", max_title, severityToString(scores.highest_severity));
    strncpy(scores.primary_alert_detail, max_detail, sizeof(scores.primary_alert_detail) - 1);

    return scores;
}

// ---------------------------------------------------------------------------
// Flood Risk  (0–100 pts)
// ---------------------------------------------------------------------------
float LocalFusionEngine::computeFloodRisk(const SensorReadings& r, char* out, size_t n) {
    float level  = 0.0f, rate = 0.0f, rain = 0.0f, probe = 0.0f;

    if      (r.water_level_cm >= WATER_LEVEL_CRITICAL_CM)  level = 40.0f;
    else if (r.water_level_cm >= WATER_LEVEL_WARNING_CM)
        level = 20.0f + ((r.water_level_cm - WATER_LEVEL_WARNING_CM) /
               (WATER_LEVEL_CRITICAL_CM - WATER_LEVEL_WARNING_CM)) * 20.0f;
    else if (r.water_level_cm > 15.0f)
        level = (r.water_level_cm / WATER_LEVEL_WARNING_CM) * 20.0f;

    if      (r.water_rate_of_rise_cm_min >= WATER_RISE_RATE_CRITICAL_CM_PER_MIN) rate = 30.0f;
    else if (r.water_rate_of_rise_cm_min > 2.0f)
        rate = (r.water_rate_of_rise_cm_min / WATER_RISE_RATE_CRITICAL_CM_PER_MIN) * 30.0f;

    rain  = (r.rain_intensity_pct / 100.0f) * 20.0f;
    probe = (r.water_level_raw > 1500) ? 10.0f : 0.0f;

    float s = constrain(level + rate + rain + probe, 0.0f, 100.0f);

    if      (s >= 75.0f) snprintf(out, n, "Water %.1fcm +%.1fcm/min Rain%.0f%%",
                                  r.water_level_cm, r.water_rate_of_rise_cm_min, r.rain_intensity_pct);
    else if (s >= 50.0f) snprintf(out, n, "Elevated water %.1fcm", r.water_level_cm);
    else                 snprintf(out, n, "Normal drainage flow");
    return s;
}

// ---------------------------------------------------------------------------
// Fire Risk  (0–100 pts)
// ---------------------------------------------------------------------------
float LocalFusionEngine::computeFireRisk(const SensorReadings& r, char* out, size_t n) {
    float flame = r.flame_detected ? 45.0f : 0.0f;
    float smoke = (r.mq2_anomaly_idx / 100.0f) * 25.0f;
    float co    = (r.mq7_anomaly_idx / 100.0f) * 15.0f;
    float temp  = 0.0f;
    if      (r.temperature_c > TEMP_CRITICAL_C)  temp = 15.0f;
    else if (r.temperature_c > 40.0f) temp = ((r.temperature_c - 40.0f) / 10.0f) * 15.0f;

    float s = flame + smoke + co + temp;

    if (!r.flame_detected && (smoke > 15.0f || co > 10.0f)) {
        _consecutive_fire_spikes++;
        if (_consecutive_fire_spikes < 3) s *= 0.5f;
    } else {
        _consecutive_fire_spikes = r.flame_detected ? 5 : 0;
    }

    s = constrain(s, 0.0f, 100.0f);
    if      (s >= 75.0f && r.flame_detected) snprintf(out, n, "Flame detected + Smoke%.0f%%", r.mq2_anomaly_idx);
    else if (s >= 75.0f)  snprintf(out, n, "Smoke%.0f%% CO%.0f%% Temp%.1fC",
                                   r.mq2_anomaly_idx, r.mq7_anomaly_idx, r.temperature_c);
    else if (s >= 50.0f)  snprintf(out, n, "Smoke/CO anomaly detected");
    else                  snprintf(out, n, "No combustion hazards");
    return s;
}

// ---------------------------------------------------------------------------
// Pollution Risk  (0–100 pts)
// ---------------------------------------------------------------------------
float LocalFusionEngine::computePollutionRisk(const SensorReadings& r, char* out, size_t n) {
    float mq2 = (r.mq2_anomaly_idx / 100.0f) * 30.0f;
    float mq7 = (r.mq7_anomaly_idx / 100.0f) * 35.0f;
    float bme = 0.0f;
    if (r.health_bme680 == SensorHealthState::ONLINE && r.gas_resistance_ohms > 0.0f) {
        if      (r.gas_resistance_ohms < 20000.0f) bme = 35.0f;
        else if (r.gas_resistance_ohms < 80000.0f)
            bme = ((80000.0f - r.gas_resistance_ohms) / 60000.0f) * 35.0f;
    }

    float s = mq2 + mq7 + bme;
    if (s > 30.0f) {
        _consecutive_pollution_spikes++;
        if (_consecutive_pollution_spikes < 3) s *= 0.6f;
    } else { _consecutive_pollution_spikes = 0; }

    s = constrain(s, 0.0f, 100.0f);
    if      (s >= 75.0f) snprintf(out, n, "High VOC/CO: MQ7=%.0f%% MQ2=%.0f%%", r.mq7_anomaly_idx, r.mq2_anomaly_idx);
    else if (s >= 50.0f) snprintf(out, n, "Moderate air quality issue");
    else                 snprintf(out, n, "Air quality nominal");
    return s;
}

// ---------------------------------------------------------------------------
// Extreme Heat Risk  (0–100 pts)
// ---------------------------------------------------------------------------
float LocalFusionEngine::computeHeatRisk(const SensorReadings& r, char* out, size_t n) {
    float temp_pts = 0.0f;
    if      (r.temperature_c >= TEMP_HEAT_CRITICAL_C)
        temp_pts = 60.0f;
    else if (r.temperature_c >= TEMP_HEAT_WARNING_C)
        temp_pts = ((r.temperature_c - TEMP_HEAT_WARNING_C) /
                    (TEMP_HEAT_CRITICAL_C - TEMP_HEAT_WARNING_C)) * 60.0f;

    // Humidity amplification: high humidity raises apparent heat index
    float hum_amp = 0.0f;
    if (r.humidity_pct >= 70.0f && temp_pts > 0.0f)
        hum_amp = ((r.humidity_pct - 70.0f) / 30.0f) * 20.0f;

    // Low humidity extreme dryness amplification (fire weather)
    float dry_amp = 0.0f;
    if (r.humidity_pct < 20.0f && temp_pts > 10.0f)
        dry_amp = 20.0f * (1.0f - r.humidity_pct / 20.0f);

    float s = constrain(temp_pts + hum_amp + dry_amp, 0.0f, 100.0f);

    if      (s >= 75.0f) snprintf(out, n, "Extreme heat %.1fC Hum %.0f%%", r.temperature_c, r.humidity_pct);
    else if (s >= 50.0f) snprintf(out, n, "High temp %.1fC warning", r.temperature_c);
    else                 snprintf(out, n, "Temperature normal");
    return s;
}

// ---------------------------------------------------------------------------
// Landslide Precursor Risk  (0–100 pts)
// ---------------------------------------------------------------------------
float LocalFusionEngine::computeLandslideRisk(const SensorReadings& r, char* out, size_t n) {
    // 1. Soil saturation (0–40 pts)
    float soil_pts = 0.0f;
    if      (r.soil_moisture_pct >= SOIL_MOISTURE_CRITICAL_PCT) soil_pts = 40.0f;
    else if (r.soil_moisture_pct >= SOIL_MOISTURE_WARNING_PCT)
        soil_pts = ((r.soil_moisture_pct - SOIL_MOISTURE_WARNING_PCT) /
                    (SOIL_MOISTURE_CRITICAL_PCT - SOIL_MOISTURE_WARNING_PCT)) * 40.0f;
    else if (r.soil_moisture_pct > 40.0f)
        soil_pts = (r.soil_moisture_pct / SOIL_MOISTURE_WARNING_PCT) * 15.0f;

    // 2. Vibration burst (0–35 pts)
    float vib_pts = 0.0f;
    if      (r.vibration_hits >= VIBRATION_CRITICAL_HITS) vib_pts = 35.0f;
    else if (r.vibration_hits >= VIBRATION_WARNING_HITS)
        vib_pts = ((float)(r.vibration_hits - VIBRATION_WARNING_HITS) /
                   (float)(VIBRATION_CRITICAL_HITS - VIBRATION_WARNING_HITS)) * 35.0f;

    // 3. Rain correlation (0–25 pts) — heavy rain + saturated soil = high risk
    float rain_pts = 0.0f;
    if (r.rain_intensity_pct > 40.0f && r.soil_moisture_pct > 50.0f)
        rain_pts = (r.rain_intensity_pct / 100.0f) * 25.0f;

    float s = soil_pts + vib_pts + rain_pts;

    // Require 3 consecutive readings above threshold before scoring > 50
    if (s > 30.0f) {
        _consecutive_landslide_spikes++;
        if (_consecutive_landslide_spikes < 3 && s > 50.0f) s = 50.0f;
    } else { _consecutive_landslide_spikes = 0; }

    s = constrain(s, 0.0f, 100.0f);

    if      (s >= 75.0f) snprintf(out, n, "Soil %.0f%% Vibr:%u Rain:%.0f%%",
                                  r.soil_moisture_pct, r.vibration_hits, r.rain_intensity_pct);
    else if (s >= 50.0f) snprintf(out, n, "Elevated saturation %.0f%%", r.soil_moisture_pct);
    else                 snprintf(out, n, "Ground conditions stable");
    return s;
}
