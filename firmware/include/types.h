#pragma once

#include <Arduino.h>

/**
 * Sensor Health Enumeration
 */
enum class SensorHealthState {
    ONLINE,      // Sensor reading normally within nominal range
    DEGRADED,    // Sensor noisy, intermittently reporting, or partially failing
    OFFLINE,     // Sensor disconnected or not responding to I2C/GPIO
    INVALID,     // Sensor producing impossible physical values (e.g. 150 deg C or negative resistance)
    CALIBRATING  // Sensor in warm-up/calibration phase
};

inline const char* sensorHealthToString(SensorHealthState state) {
    switch (state) {
        case SensorHealthState::ONLINE: return "ONLINE";
        case SensorHealthState::DEGRADED: return "DEGRADED";
        case SensorHealthState::OFFLINE: return "OFFLINE";
        case SensorHealthState::INVALID: return "INVALID";
        case SensorHealthState::CALIBRATING: return "CALIBRATING";
        default: return "UNKNOWN";
    }
}

/**
 * Hazard Severity Level
 */
enum class HazardSeverity {
    NORMAL = 0,   // 0 - 24
    LOW = 1,      // 25 - 49
    WARNING = 2,  // 50 - 74
    CRITICAL = 3  // 75 - 100
};

inline const char* severityToString(HazardSeverity sev) {
    switch (sev) {
        case HazardSeverity::NORMAL: return "NORMAL";
        case HazardSeverity::LOW: return "LOW";
        case HazardSeverity::WARNING: return "WARNING";
        case HazardSeverity::CRITICAL: return "CRITICAL";
        default: return "NORMAL";
    }
}

/**
 * Aggregated Sensor Readings Snapshot
 */
struct SensorReadings {
    // Environmental Atmospheric (BME680 / DHT22)
    float temperature_c = 0.0f;
    float humidity_pct = 0.0f;
    float pressure_hpa = 0.0f;
    float gas_resistance_ohms = 0.0f;

    // Gas & Combustion Anomaly Sensors (Raw ADC & Normalized 0-100% anomaly index)
    uint16_t mq2_raw = 0;
    uint16_t mq7_raw = 0;
    float mq2_anomaly_idx = 0.0f;
    float mq7_anomaly_idx = 0.0f;

    // Hydrological
    uint16_t rain_raw = 0;             // FC-37 ADC (0-4095, lower = wetter)
    float rain_intensity_pct = 0.0f;   // 0% (Dry) to 100% (Torrential)
    uint16_t water_level_raw = 0;      // Conductive probe ADC (0-4095)
    float ultrasonic_dist_cm = 0.0f;   // HC-SR04 direct distance
    float water_level_cm = 0.0f;       // Derived water depth in channel
    float water_rate_of_rise_cm_min = 0.0f; // Delta height / Delta time

    // Optical
    bool flame_detected = false;       // Digital flame sensor

    // System Diagnostics
    float battery_voltage = 3.7f;
    int8_t wifi_rssi_dbm = 0;
    uint32_t sample_timestamp_ms = 0;

    // Sensor Health Flags
    SensorHealthState health_bme680 = SensorHealthState::CALIBRATING;
    SensorHealthState health_dht22 = SensorHealthState::CALIBRATING;
    SensorHealthState health_mq2 = SensorHealthState::CALIBRATING;
    SensorHealthState health_mq7 = SensorHealthState::CALIBRATING;
    SensorHealthState health_rain = SensorHealthState::CALIBRATING;
    SensorHealthState health_ultrasonic = SensorHealthState::CALIBRATING;
    SensorHealthState health_water_probe = SensorHealthState::CALIBRATING;
    SensorHealthState health_flame = SensorHealthState::CALIBRATING;
};

/**
 * Calculated Hazard Scores (Normalized 0 to 100)
 */
struct HazardScores {
    float flood_score = 0.0f;
    float fire_score = 0.0f;
    float pollution_score = 0.0f;

    HazardSeverity flood_severity = HazardSeverity::NORMAL;
    HazardSeverity fire_severity = HazardSeverity::NORMAL;
    HazardSeverity pollution_severity = HazardSeverity::NORMAL;
    HazardSeverity highest_severity = HazardSeverity::NORMAL;

    // Short reason strings for OLED display & diagnostics
    char primary_alert_title[32] = "NORMAL";
    char primary_alert_detail[64] = "Conditions nominal";
};

/**
 * Full Telemetry Packet for Serialization & Buffering
 */
struct TelemetryPacket {
    char node_id[16];
    char firmware_ver[16];
    uint32_t sequence_id;
    uint32_t epoch_timestamp;
    float latitude;
    float longitude;

    SensorReadings readings;
    HazardScores scores;
};
