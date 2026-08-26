#pragma once

/**
 * ============================================================================
 * Environmental Intelligence Network — ESP32 Edge Node
 * Hardware Configuration & Pin Mapping
 * Target Board: ESP32-WROOM-32 (30-Pin Dev Board)
 * Power:  USB 5V (laptop) -> onboard 3.3V regulator
 * ============================================================================
 */

// Node Identification — change NODE_ID before flashing each physical node
#define NODE_ID          "NODE_001"          // NODE_001..NODE_004
#define FIRMWARE_VERSION "v2.0.0-ein"
#define NODE_LATITUDE    28.6139f
#define NODE_LONGITUDE   77.2090f

// ----------------------------------------------------------------------------
// GPIO Pin Mapping
// ----------------------------------------------------------------------------

// I2C Bus  (BME680 + OLED share the same bus)
#define PIN_I2C_SDA          21
#define PIN_I2C_SCL          22
#define OLED_I2C_ADDRESS     0x3C
#define OLED_SCREEN_WIDTH    128
#define OLED_SCREEN_HEIGHT   64

// Display Driver Selection:
// Set to 1 for 1.3" I2C OLED (SH1106 / SH1106G controller - standard for 1.3")
// Set to 0 for 0.96" I2C OLED (SSD1306 controller - standard for 0.96")
#define USE_SH1106_1_3_INCH  1

#define BME680_I2C_ADDRESS   0x77   // Primary address (try 0x76 if 0x77 fails)

// DHT22 auxiliary temperature/humidity
#define PIN_DHT22            19

// Gas & combustion (input-only ADC1 pins, no pull-up/down)
#define PIN_MQ2_ANALOG       34    // Smoke / combustible gas
#define PIN_MQ7_ANALOG       35    // Carbon monoxide (CO)

// Hydrological
#define PIN_FC37_RAIN        33    // Rain intensity (ADC1_CH5)
#define PIN_WATER_LEVEL_ANALOG 32  // Conductive water probe (ADC1_CH4)
#define PIN_HCSR04_TRIG       5   // HC-SR04 ultrasonic trigger
#define PIN_HCSR04_ECHO      18   // HC-SR04 ultrasonic echo

// Ground stability (new sensors)
// FC-28 soil moisture — resistive probe, ADC: low = wet, high = dry
#define PIN_SOIL_MOISTURE_ANALOG  39   // GPIO 39 (input-only ADC1_CH3) ← confirm wiring

// SW-420 vibration sensor — digital, HIGH pulse on vibration event
#define PIN_VIBRATION_DIGITAL     23   // GPIO 23 ← confirm wiring

// Fire / optical
#define PIN_FLAME_DIGITAL    25    // Digital flame sensor (Active LOW)

// Actuators
#define PIN_BUZZER_2N2222A   26    // Active buzzer via 2N2222A transistor base
#define PIN_LED_RED          27    // Critical status indicator
#define PIN_LED_YELLOW       14    // Warning status indicator
#define PIN_LED_GREEN        13    // Normal / 1 Hz heartbeat

// ----------------------------------------------------------------------------
// Timing (milliseconds)
// ----------------------------------------------------------------------------
#define SENSOR_READ_INTERVAL_MS      1000   // Sample sensors every 1 s
#define TELEMETRY_SEND_INTERVAL_MS   3000   // Send telemetry every 3 s
#define OLED_REFRESH_INTERVAL_MS      500   // Refresh OLED at 2 Hz
#define HEARTBEAT_LED_INTERVAL_MS    1000   // Green LED blink period
#define VIBRATION_COUNT_WINDOW_MS    1000   // Count SW-420 pulses per 1 s window

// Offline buffer (packets cached during Wi-Fi disconnect before re-transmit)
#define TELEMETRY_RING_BUFFER_CAPACITY  120

// ----------------------------------------------------------------------------
// Ultrasonic sensor calibration
// ----------------------------------------------------------------------------
#define SENSOR_MOUNT_HEIGHT_CM    100.0f   // Distance: sensor face -> dry channel bottom
#define ULTRASONIC_MIN_DISTANCE_CM  2.0f
#define ULTRASONIC_MAX_DISTANCE_CM 400.0f

// ----------------------------------------------------------------------------
// FC-28 Soil Moisture calibration
// Resistive probe: lower ADC = more water (inverted scale)
// Calibrate with probe in dry air and fully submerged for your specific probe.
// ----------------------------------------------------------------------------
#define SOIL_MOISTURE_DRY_ADC   3500   // ADC reading in dry air
#define SOIL_MOISTURE_WET_ADC    800   // ADC reading fully submerged

// ----------------------------------------------------------------------------
// Hazard thresholds (on-device local fusion)
// ----------------------------------------------------------------------------
#define THRESHOLD_NORMAL_MAX  24
#define THRESHOLD_LOW_MAX     49
#define THRESHOLD_WARNING_MAX 74
#define THRESHOLD_CRITICAL_MIN 75

// Flood
#define WATER_LEVEL_WARNING_CM         35.0f
#define WATER_LEVEL_CRITICAL_CM        65.0f
#define WATER_RISE_RATE_CRITICAL_CM_PER_MIN  6.0f

// Fire / smoke
#define TEMP_CRITICAL_C                50.0f
#define TEMP_RISE_RATE_CRITICAL_C_PER_MIN  4.0f

// Extreme heat (distinct from fire)
#define TEMP_HEAT_WARNING_C            42.0f
#define TEMP_HEAT_CRITICAL_C           50.0f

// Landslide precursors
#define SOIL_MOISTURE_WARNING_PCT      65.0f
#define SOIL_MOISTURE_CRITICAL_PCT     85.0f
#define VIBRATION_WARNING_HITS         10     // hits per 1 s window
#define VIBRATION_CRITICAL_HITS        30

// ----------------------------------------------------------------------------
// Wi-Fi & Backend configuration
// Edit WIFI_SSID, WIFI_PASS and BACKEND_HOST to match your network.
// BACKEND_HOST should be the LAN IP of the laptop running the Python server.
// ----------------------------------------------------------------------------
#define WIFI_SSID        "YOUR_WIFI_SSID"
#define WIFI_PASS        "YOUR_WIFI_PASSWORD"
#define BACKEND_HOST     "192.168.1.100"   // Laptop IP on LAN
#define BACKEND_PORT     8000
#define BACKEND_PATH     "/api/telemetry"
#define BACKEND_AUTH     "Bearer ein-node-token-2026"
#define WIFI_CONNECT_TIMEOUT_MS  15000     // 15 s connection timeout
