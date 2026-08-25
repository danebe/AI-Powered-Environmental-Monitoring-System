#pragma once

#include <Arduino.h>

/**
 * Sensor Health State
 */
enum class SensorHealthState {
    ONLINE,       // Reading normally within nominal range
    DEGRADED,     // Noisy, intermittent, or partially failing
    OFFLINE,      // Disconnected or not responding
    INVALID,      // Producing physically impossible values
    CALIBRATING   // In warm-up / calibration phase
};

inline const char* sensorHealthToString(SensorHealthState s) {
    switch (s) {
        case SensorHealthState::ONLINE:      return "ONLINE";
        case SensorHealthState::DEGRADED:    return "DEGRADED";
        case SensorHealthState::OFFLINE:     return "OFFLINE";
        case SensorHealthState::INVALID:     return "INVALID";
        case SensorHealthState::CALIBRATING: return "CALIBRATING";
        default: return "UNKNOWN";
    }
}

/**
 * Hazard Severity Level
 */
enum class HazardSeverity {
    NORMAL   = 0,   // 0  – 24
    LOW      = 1,   // 25 – 49
    WARNING  = 2,   // 50 – 74
    CRITICAL = 3    // 75 – 100
};

inline const char* severityToString(HazardSeverity s) {
    switch (s) {
        case HazardSeverity::NORMAL:   return "NORMAL";
        case HazardSeverity::LOW:      return "LOW";
        case HazardSeverity::WARNING:  return "WARNING";
        case HazardSeverity::CRITICAL: return "CRITICAL";
        default: return "NORMAL";
    }
}

/**
 * Aggregated Sensor Readings Snapshot
 */
struct SensorReadings {
    // Atmospheric  (BME680 primary / DHT22 fallback)
    float    temperature_c       = 0.0f;
    float    humidity_pct        = 0.0f;
    float    pressure_hpa        = 0.0f;
    float    gas_resistance_ohms = 0.0f;

    // Gas & combustion (raw ADC + normalised anomaly index 0–100 %)
    uint16_t mq2_raw             = 0;
    uint16_t mq7_raw             = 0;
    float    mq2_anomaly_idx     = 0.0f;
    float    mq7_anomaly_idx     = 0.0f;

    // Hydrological
    uint16_t rain_raw                   = 0;
    float    rain_intensity_pct         = 0.0f;
    uint16_t water_level_raw            = 0;
    float    ultrasonic_dist_cm         = 0.0f;
    float    water_level_cm             = 0.0f;
    float    water_rate_of_rise_cm_min  = 0.0f;

    // Ground stability
    uint16_t soil_moisture_raw   = 0;    // FC-28 raw ADC (lower = wetter)
    float    soil_moisture_pct   = 0.0f; // 0 % dry → 100 % saturated
    uint16_t vibration_hits      = 0;    // SW-420 pulse count per sampling window

    // Water quality (optional analog probes; left at defaults if not wired)
    float    water_ph            = 7.0f;
    float    water_turbidity_ntu = 0.0f;

    // Optical
    bool     flame_detected      = false;

    // Diagnostics
    int8_t   wifi_rssi_dbm       = 0;
    uint32_t sample_timestamp_ms = 0;

    // Sensor health flags
    SensorHealthState health_bme680       = SensorHealthState::CALIBRATING;
    SensorHealthState health_dht22        = SensorHealthState::CALIBRATING;
    SensorHealthState health_mq2          = SensorHealthState::CALIBRATING;
    SensorHealthState health_mq7          = SensorHealthState::CALIBRATING;
    SensorHealthState health_rain         = SensorHealthState::CALIBRATING;
    SensorHealthState health_ultrasonic   = SensorHealthState::CALIBRATING;
    SensorHealthState health_water_probe  = SensorHealthState::CALIBRATING;
    SensorHealthState health_flame        = SensorHealthState::CALIBRATING;
    SensorHealthState health_soil         = SensorHealthState::CALIBRATING;
    SensorHealthState health_vibration    = SensorHealthState::CALIBRATING;
};

/**
 * Calculated Hazard Scores (0–100 each)
 */
struct HazardScores {
    float flood_score        = 0.0f;
    float fire_score         = 0.0f;
    float pollution_score    = 0.0f;
    float heat_score         = 0.0f;
    float landslide_score    = 0.0f;
    float industrial_score   = 0.0f;
    float water_quality_score = 0.0f;

    HazardSeverity flood_severity         = HazardSeverity::NORMAL;
    HazardSeverity fire_severity          = HazardSeverity::NORMAL;
    HazardSeverity pollution_severity     = HazardSeverity::NORMAL;
    HazardSeverity heat_severity          = HazardSeverity::NORMAL;
    HazardSeverity landslide_severity     = HazardSeverity::NORMAL;
    HazardSeverity industrial_severity    = HazardSeverity::NORMAL;
    HazardSeverity water_quality_severity = HazardSeverity::NORMAL;
    HazardSeverity highest_severity       = HazardSeverity::NORMAL;

    char primary_alert_title[32]  = "NORMAL";
    char primary_alert_detail[64] = "Conditions nominal";
};

/**
 * Full Telemetry Packet sent to backend over Wi-Fi (JSON)
 */
struct TelemetryPacket {
    char     node_id[16];
    char     firmware_ver[16];
    uint32_t sequence_id;
    uint32_t epoch_timestamp;
    float    latitude;
    float    longitude;

    SensorReadings readings;
    HazardScores   scores;
};
