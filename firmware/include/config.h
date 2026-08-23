#pragma once

/**
 * ============================================================================
 * SIH 2026 Resilient Environmental Monitoring Network
 * ESP32 Hardware Configuration & Pin Mapping
 * Target Board: ESP32-WROOM-32 (30-Pin Dev Board)
 * ============================================================================
 */

// Node Identification
#define NODE_ID "NODE_001"
#define FIRMWARE_VERSION "v1.4.0-sih2026"
#define NODE_LATITUDE 28.6139f   // Mock field coordinate: Latitude (e.g. New Delhi / Forest Edge)
#define NODE_LONGITUDE 77.2090f  // Mock field coordinate: Longitude

// ----------------------------------------------------------------------------
// GPIO Pin Mapping (Strictly matches hardware specifications)
// ----------------------------------------------------------------------------

// I2C Bus (Shared between BME680 Sensor & SSD1306 OLED Display)
#define PIN_I2C_SDA 21
#define PIN_I2C_SCL 22
#define OLED_I2C_ADDRESS 0x3C
#define OLED_SCREEN_WIDTH 128
#define OLED_SCREEN_HEIGHT 64
#define BME680_I2C_ADDRESS 0x77 // Primary BME680 address (or 0x76)

// DHT22 Auxiliary Temperature & Humidity Sensor
#define PIN_DHT22 19

// Gas & Combustion Anomaly Sensors (Input-Only ADC1 Pins)
// Note: GPIO 34-39 are input-only on ESP32 and have no internal pull-up/down
#define PIN_MQ2_ANALOG 34   // Gas / Smoke analog signal
#define PIN_MQ7_ANALOG 35   // CO / Combustion analog signal

// Water & Rain Sensors
#define PIN_FC37_RAIN 33            // Analog Rain intensity sensor (ADC1_CH5)
#define PIN_WATER_LEVEL_ANALOG 32   // Conductive water level sensor (ADC1_CH4)
#define PIN_HCSR04_TRIG 5           // HC-SR04 Ultrasonic Trigger
#define PIN_HCSR04_ECHO 18          // HC-SR04 Ultrasonic Echo

// Optical / Fire Hazard
#define PIN_FLAME_DIGITAL 25        // Digital Flame detection (Active LOW or HIGH depending on module)

// Actuators & Indicators
#define PIN_BUZZER_2N2222A 26       // Active Buzzer driving transistor (2N2222A Base)
#define PIN_LED_RED 27              // Critical Status Indicator
#define PIN_LED_YELLOW 14           // Warning Status Indicator
#define PIN_LED_GREEN 13            // Normal / Heartbeat Status Indicator

// ----------------------------------------------------------------------------
// Sensor Sampling & Telemetry Timers (Milliseconds)
// ----------------------------------------------------------------------------
#define SENSOR_READ_INTERVAL_MS 1000      // Read sensors every 1 second
#define TELEMETRY_SEND_INTERVAL_MS 3000   // Transmit telemetry every 3 seconds
#define OLED_REFRESH_INTERVAL_MS 500      // Refresh local display at 2 Hz
#define HEARTBEAT_LED_INTERVAL_MS 1000    // Green LED pulse interval

// Offline Telemetry Buffer Size (Number of packets saved during Wi-Fi disconnect)
#define TELEMETRY_RING_BUFFER_CAPACITY 120

// ----------------------------------------------------------------------------
// Ultrasonic Sensor Calibration (Centimeters)
// ----------------------------------------------------------------------------
#define SENSOR_MOUNT_HEIGHT_CM 100.0f     // Distance from sensor face to dry channel bottom
#define ULTRASONIC_MIN_DISTANCE_CM 2.0f   // Minimum valid HC-SR04 distance
#define ULTRASONIC_MAX_DISTANCE_CM 400.0f // Maximum valid HC-SR04 distance

// ----------------------------------------------------------------------------
// Default Hazard Thresholds (Configurable)
// ----------------------------------------------------------------------------
#define THRESHOLD_NORMAL_MAX 24
#define THRESHOLD_LOW_MAX 49
#define THRESHOLD_WARNING_MAX 74
#define THRESHOLD_CRITICAL_MIN 75

// Water Level Thresholds (cm from channel bottom)
#define WATER_LEVEL_WARNING_CM 35.0f
#define WATER_LEVEL_CRITICAL_CM 65.0f
#define WATER_RISE_RATE_CRITICAL_CM_PER_MIN 6.0f // Rate of rise indicating flash flood

// Flame & Temperature Fire Thresholds
#define TEMP_CRITICAL_C 50.0f
#define TEMP_RISE_RATE_CRITICAL_C_PER_MIN 4.0f

// ----------------------------------------------------------------------------
// Wi-Fi & Backend Endpoint Configuration
// ----------------------------------------------------------------------------
#define DEFAULT_WIFI_SSID "SIH_FIELD_NETWORK"
#define DEFAULT_WIFI_PASS "ResilientMesh2026"
#define BACKEND_HTTP_URL "http://192.168.1.100:8000/api/telemetry"
#define BACKEND_AUTH_TOKEN "Bearer sih-node-token-sec-2026"
