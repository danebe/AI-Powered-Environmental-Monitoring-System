#include "local_fusion.h"
#include <stdio.h>
#include <string.h>

LocalFusionEngine::LocalFusionEngine()
    : _consecutive_fire_spikes(0)
    , _consecutive_pollution_spikes(0)
{
}

HazardSeverity LocalFusionEngine::scoreToSeverity(float score) {
    if (score >= THRESHOLD_CRITICAL_MIN) return HazardSeverity::CRITICAL;
    if (score >= 50.0f) return HazardSeverity::WARNING;
    if (score >= 25.0f) return HazardSeverity::LOW;
    return HazardSeverity::NORMAL;
}

HazardScores LocalFusionEngine::evaluate(const SensorReadings& r) {
    HazardScores scores;
    char reason[64] = {0};

    char flood_reason[64] = {0};
    char fire_reason[64] = {0};
    char pollution_reason[64] = {0};

    scores.flood_score = computeFloodRisk(r, flood_reason, sizeof(flood_reason));
    scores.fire_score = computeFireRisk(r, fire_reason, sizeof(fire_reason));
    scores.pollution_score = computePollutionRisk(r, pollution_reason, sizeof(pollution_reason));

    scores.flood_severity = scoreToSeverity(scores.flood_score);
    scores.fire_severity = scoreToSeverity(scores.fire_score);
    scores.pollution_severity = scoreToSeverity(scores.pollution_score);

    // Determine highest overall hazard
    float max_score = scores.flood_score;
    scores.highest_severity = scores.flood_severity;
    snprintf(scores.primary_alert_title, sizeof(scores.primary_alert_title), "FLOOD: %s", severityToString(scores.flood_severity));
    strncpy(scores.primary_alert_detail, flood_reason, sizeof(scores.primary_alert_detail));

    if (scores.fire_score > max_score) {
        max_score = scores.fire_score;
        scores.highest_severity = scores.fire_severity;
        snprintf(scores.primary_alert_title, sizeof(scores.primary_alert_title), "FIRE: %s", severityToString(scores.fire_severity));
        strncpy(scores.primary_alert_detail, fire_reason, sizeof(scores.primary_alert_detail));
    }

    if (scores.pollution_score > max_score) {
        max_score = scores.pollution_score;
        scores.highest_severity = scores.pollution_severity;
        snprintf(scores.primary_alert_title, sizeof(scores.primary_alert_title), "POLLUTION: %s", severityToString(scores.pollution_severity));
        strncpy(scores.primary_alert_detail, pollution_reason, sizeof(scores.primary_alert_detail));
    }

    if (max_score < 25.0f) {
        strncpy(scores.primary_alert_title, "ENV NORMAL", sizeof(scores.primary_alert_title));
        strncpy(scores.primary_alert_detail, "All sensor channels nominal", sizeof(scores.primary_alert_detail));
    }

    return scores;
}

float LocalFusionEngine::computeFloodRisk(const SensorReadings& r, char* reason_out, size_t max_len) {
    // 1. Water Level contribution (0-40 points)
    float level_contrib = 0.0f;
    if (r.water_level_cm > WATER_LEVEL_CRITICAL_CM) {
        level_contrib = 40.0f;
    } else if (r.water_level_cm > WATER_LEVEL_WARNING_CM) {
        level_contrib = 20.0f + ((r.water_level_cm - WATER_LEVEL_WARNING_CM) / (WATER_LEVEL_CRITICAL_CM - WATER_LEVEL_WARNING_CM)) * 20.0f;
    } else if (r.water_level_cm > 15.0f) {
        level_contrib = (r.water_level_cm / WATER_LEVEL_WARNING_CM) * 20.0f;
    }

    // 2. Rate of Rise contribution (0-30 points)
    float rate_contrib = 0.0f;
    if (r.water_rate_of_rise_cm_min > WATER_RISE_RATE_CRITICAL_CM_PER_MIN) {
        rate_contrib = 30.0f;
    } else if (r.water_rate_of_rise_cm_min > 2.0f) {
        rate_contrib = (r.water_rate_of_rise_cm_min / WATER_RISE_RATE_CRITICAL_CM_PER_MIN) * 30.0f;
    }

    // 3. Rain Intensity contribution (0-20 points)
    float rain_contrib = (r.rain_intensity_pct / 100.0f) * 20.0f;

    // 4. Conductive Probe Confirmation (0-10 points)
    float probe_contrib = (r.water_level_raw > 1500) ? 10.0f : 0.0f;

    float total_score = level_contrib + rate_contrib + rain_contrib + probe_contrib;
    total_score = constrain(total_score, 0.0f, 100.0f);

    if (total_score >= 75.0f) {
        snprintf(reason_out, max_len, "Water %0.1fcm rising %0.1fcm/m + Rain %0.0f%%", r.water_level_cm, r.water_rate_of_rise_cm_min, r.rain_intensity_pct);
    } else if (total_score >= 50.0f) {
        snprintf(reason_out, max_len, "Elevated water %0.1fcm, Rain %0.0f%%", r.water_level_cm, r.rain_intensity_pct);
    } else {
        snprintf(reason_out, max_len, "Normal drainage flow");
    }

    return total_score;
}

float LocalFusionEngine::computeFireRisk(const SensorReadings& r, char* reason_out, size_t max_len) {
    // 1. Flame Sensor (0 or 45 points)
    float flame_contrib = r.flame_detected ? 45.0f : 0.0f;

    // 2. Smoke Anomaly (MQ-2) (0-25 points)
    float smoke_contrib = (r.mq2_anomaly_idx / 100.0f) * 25.0f;

    // 3. CO Combustion Anomaly (MQ-7) (0-15 points)
    float co_contrib = (r.mq7_anomaly_idx / 100.0f) * 15.0f;

    // 4. Extreme Temperature or High Heat (0-15 points)
    float temp_contrib = 0.0f;
    if (r.temperature_c > TEMP_CRITICAL_C) {
        temp_contrib = 15.0f;
    } else if (r.temperature_c > 40.0f) {
        temp_contrib = ((r.temperature_c - 40.0f) / 10.0f) * 15.0f;
    }

    float raw_score = flame_contrib + smoke_contrib + co_contrib + temp_contrib;

    // Noise persistence check: single spike without flame requires consecutive verification
    if (!r.flame_detected && (smoke_contrib > 15.0f || co_contrib > 10.0f)) {
        _consecutive_fire_spikes++;
        if (_consecutive_fire_spikes < 3) {
            raw_score = raw_score * 0.5f; // Dampen first 2 transient spikes
        }
    } else if (r.flame_detected) {
        _consecutive_fire_spikes = 5;
    } else {
        _consecutive_fire_spikes = 0;
    }

    float total_score = constrain(raw_score, 0.0f, 100.0f);

    if (total_score >= 75.0f) {
        if (r.flame_detected) {
            snprintf(reason_out, max_len, "Optical flame detected + Smoke %0.0f%%", r.mq2_anomaly_idx);
        } else {
            snprintf(reason_out, max_len, "Heavy smoke %0.0f%%, CO %0.0f%%, Temp %0.1fC", r.mq2_anomaly_idx, r.mq7_anomaly_idx, r.temperature_c);
        }
    } else if (total_score >= 50.0f) {
        snprintf(reason_out, max_len, "Smoke/CO anomaly detected");
    } else {
        snprintf(reason_out, max_len, "No combustion hazards");
    }

    return total_score;
}

float LocalFusionEngine::computePollutionRisk(const SensorReadings& r, char* reason_out, size_t max_len) {
    // 1. MQ-2 Persistent Anomaly (0-30 points)
    float mq2_contrib = (r.mq2_anomaly_idx / 100.0f) * 30.0f;

    // 2. MQ-7 Persistent CO Anomaly (0-35 points)
    float mq7_contrib = (r.mq7_anomaly_idx / 100.0f) * 35.0f;

    // 3. BME680 Gas Resistance Drop (Lower resistance = higher VOCs) (0-35 points)
    float bme_contrib = 0.0f;
    if (r.health_bme680 == SensorHealthState::ONLINE && r.gas_resistance_ohms > 0.0f) {
        if (r.gas_resistance_ohms < 20000.0f) {
            bme_contrib = 35.0f;
        } else if (r.gas_resistance_ohms < 80000.0f) {
            bme_contrib = ((80000.0f - r.gas_resistance_ohms) / 60000.0f) * 35.0f;
        }
    }

    float raw_score = mq2_contrib + mq7_contrib + bme_contrib;

    // Persistence dampening to reject transient puffs
    if (raw_score > 30.0f) {
        _consecutive_pollution_spikes++;
        if (_consecutive_pollution_spikes < 3) {
            raw_score = raw_score * 0.6f;
        }
    } else {
        _consecutive_pollution_spikes = 0;
    }

    float total_score = constrain(raw_score, 0.0f, 100.0f);

    if (total_score >= 75.0f) {
        snprintf(reason_out, max_len, "High persistent VOC/CO gases: MQ7 %0.0f%%, MQ2 %0.0f%%", r.mq7_anomaly_idx, r.mq2_anomaly_idx);
    } else if (total_score >= 50.0f) {
        snprintf(reason_out, max_len, "Moderate air quality degradation");
    } else {
        snprintf(reason_out, max_len, "Air quality index clean");
    }

    return total_score;
}
