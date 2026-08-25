#include "sensor_manager.h"
#include <Wire.h>
#include <WiFi.h>
#include "../../config.h"

// Static ISR counter for SW-420 vibration sensor
volatile uint16_t SensorManager::_vibrationCount = 0;

// SW-420 vibration interrupt service routine
static void IRAM_ATTR vibrationISR() {
    SensorManager::_vibrationCount++;
}

SensorManager::SensorManager()
    : _prev_water_level_cm(0.0f)
    , _prev_water_time_ms(0)
    , _water_ema(0.0f)
    , _prev_temp_c(25.0f)
    , _prev_temp_time_ms(0)
    , _mq2_baseline(300.0f)
    , _mq7_baseline(250.0f)
    , _calibration_samples(0)
{}

void SensorManager::begin() {
    // Analog ADC pins (input-only pins need no pinMode in most cases, but set anyway)
    pinMode(PIN_MQ2_ANALOG,           INPUT);
    pinMode(PIN_MQ7_ANALOG,           INPUT);
    pinMode(PIN_FC37_RAIN,            INPUT);
    pinMode(PIN_WATER_LEVEL_ANALOG,   INPUT);
    pinMode(PIN_SOIL_MOISTURE_ANALOG, INPUT);  // FC-28 soil moisture

    // Digital I/O
    pinMode(PIN_FLAME_DIGITAL,    INPUT);
    pinMode(PIN_HCSR04_TRIG,      OUTPUT);
    pinMode(PIN_HCSR04_ECHO,      INPUT);
    digitalWrite(PIN_HCSR04_TRIG, LOW);

    // SW-420 vibration sensor — interrupt on rising edge
    pinMode(PIN_VIBRATION_DIGITAL, INPUT);
    attachInterrupt(digitalPinToInterrupt(PIN_VIBRATION_DIGITAL), vibrationISR, RISING);

    // I2C bus for BME680 and OLED
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 100000);  // 100 kHz

    // ADC range: 11 dB attenuation → 0 to ~3.3 V full scale (0–4095)
    analogSetAttenuation(ADC_11db);

    _prev_water_time_ms = millis();
    _prev_temp_time_ms  = millis();

    Serial.println("[SensorManager] Initialized. FC-28 GPIO=" + String(PIN_SOIL_MOISTURE_ANALOG) +
                   "  SW-420 GPIO=" + String(PIN_VIBRATION_DIGITAL));
}

SensorReadings SensorManager::sampleAll() {
    SensorReadings r;
    r.sample_timestamp_ms = millis();

    readAtmospheric(r);
    readGasSensors(r);
    readHydrological(r);
    readSoilAndVibration(r);
    readFlame(r);
    readDiagnostics(r);

    return r;
}

// ---------------------------------------------------------------------------
// Atmospheric sensors — BME680 over I2C (with DHT22 fallback)
// ---------------------------------------------------------------------------
void SensorManager::readAtmospheric(SensorReadings& r) {
    Wire.beginTransmission(BME680_I2C_ADDRESS);
    byte err = Wire.endTransmission();

    if (err == 0) {
        // BME680 present on I2C bus
        r.health_bme680 = SensorHealthState::ONLINE;
        // --- Real hardware: include Adafruit_BME680 and uncomment below ---
        // r.temperature_c       = bme.temperature;
        // r.humidity_pct        = bme.humidity;
        // r.pressure_hpa        = bme.pressure / 100.0f;
        // r.gas_resistance_ohms = bme.gas_resistance;
        r.temperature_c       = 26.5f;
        r.humidity_pct        = 64.0f;
        r.pressure_hpa        = 1012.3f;
        r.gas_resistance_ohms = 125000.0f;
    } else {
        r.health_bme680 = SensorHealthState::OFFLINE;
        r.temperature_c       = 26.5f;
        r.humidity_pct        = 64.0f;
        r.pressure_hpa        = 1013.25f;
        r.gas_resistance_ohms = 0.0f;
        // Fallback: read DHT22 here if library included
    }

    r.health_dht22 = SensorHealthState::ONLINE;

    // Physical sanity bounds
    if (r.temperature_c < -40.0f || r.temperature_c > 85.0f) r.health_bme680 = SensorHealthState::INVALID;
    if (r.humidity_pct  <   0.0f || r.humidity_pct  > 100.0f) r.health_bme680 = SensorHealthState::INVALID;
}

// ---------------------------------------------------------------------------
// MQ-2 (smoke/combustible) and MQ-7 (CO)
// ---------------------------------------------------------------------------
void SensorManager::readGasSensors(SensorReadings& r) {
    // 8-sample average for noise rejection
    uint32_t mq2_sum = 0, mq7_sum = 0;
    for (int i = 0; i < 8; i++) {
        mq2_sum += analogRead(PIN_MQ2_ANALOG);
        mq7_sum += analogRead(PIN_MQ7_ANALOG);
        delayMicroseconds(50);
    }
    r.mq2_raw = mq2_sum / 8;
    r.mq7_raw = mq7_sum / 8;

    r.health_mq2 = (r.mq2_raw < 10) ? SensorHealthState::DEGRADED : SensorHealthState::ONLINE;
    r.health_mq7 = (r.mq7_raw < 10) ? SensorHealthState::DEGRADED : SensorHealthState::ONLINE;

    // Adaptive baseline during first 50 samples (warm-up)
    if (_calibration_samples < 50) {
        _mq2_baseline = (_mq2_baseline * 0.9f) + (r.mq2_raw * 0.1f);
        _mq7_baseline = (_mq7_baseline * 0.9f) + (r.mq7_raw * 0.1f);
        _calibration_samples++;
        r.health_mq2 = SensorHealthState::CALIBRATING;
        r.health_mq7 = SensorHealthState::CALIBRATING;
    }

    float mq2_diff = (float)r.mq2_raw - _mq2_baseline;
    r.mq2_anomaly_idx = constrain((mq2_diff / 2500.0f) * 100.0f, 0.0f, 100.0f);

    float mq7_diff = (float)r.mq7_raw - _mq7_baseline;
    r.mq7_anomaly_idx = constrain((mq7_diff / 2000.0f) * 100.0f, 0.0f, 100.0f);
}

// ---------------------------------------------------------------------------
// Hydrological — FC-37 rain, conductive probe, HC-SR04 ultrasonic
// ---------------------------------------------------------------------------
void SensorManager::readHydrological(SensorReadings& r) {
    // FC-37 rain sensor (4 sample average)
    uint32_t rain_sum = 0;
    for (int i = 0; i < 4; i++) rain_sum += analogRead(PIN_FC37_RAIN);
    r.rain_raw = rain_sum / 4;
    float inv = 4095.0f - (float)r.rain_raw;
    r.rain_intensity_pct = constrain((inv / 3000.0f) * 100.0f, 0.0f, 100.0f);
    r.health_rain = SensorHealthState::ONLINE;

    // Conductive water level probe
    r.water_level_raw    = analogRead(PIN_WATER_LEVEL_ANALOG);
    r.health_water_probe = SensorHealthState::ONLINE;

    // HC-SR04 ultrasonic distance
    digitalWrite(PIN_HCSR04_TRIG, LOW);
    delayMicroseconds(2);
    digitalWrite(PIN_HCSR04_TRIG, HIGH);
    delayMicroseconds(10);
    digitalWrite(PIN_HCSR04_TRIG, LOW);

    long us = pulseIn(PIN_HCSR04_ECHO, HIGH, 25000);
    if (us == 0) {
        r.health_ultrasonic  = SensorHealthState::DEGRADED;
        r.ultrasonic_dist_cm = SENSOR_MOUNT_HEIGHT_CM;
    } else {
        r.health_ultrasonic  = SensorHealthState::ONLINE;
        r.ultrasonic_dist_cm = (us * 0.0343f) / 2.0f;
    }

    // Derived water depth with EMA filter (alpha = 0.3)
    float raw_depth = SENSOR_MOUNT_HEIGHT_CM - r.ultrasonic_dist_cm;
    if (raw_depth < 0.0f) raw_depth = 0.0f;
    _water_ema = (_water_ema <= 0.01f) ? raw_depth : (0.3f * raw_depth + 0.7f * _water_ema);
    r.water_level_cm = _water_ema;

    r.water_rate_of_rise_cm_min = calculateWaterRateOfRise(r.water_level_cm, r.sample_timestamp_ms);
}

// ---------------------------------------------------------------------------
// FC-28 Soil Moisture + SW-420 Vibration
// ---------------------------------------------------------------------------
void SensorManager::readSoilAndVibration(SensorReadings& r) {
    // --- FC-28 Soil Moisture ---
    // Resistive probe: lower ADC reading = more water (inverted scale)
    uint32_t soil_sum = 0;
    for (int i = 0; i < 4; i++) {
        soil_sum += analogRead(PIN_SOIL_MOISTURE_ANALOG);
        delayMicroseconds(50);
    }
    r.soil_moisture_raw = soil_sum / 4;

    // Map inverted ADC to 0–100 % moisture
    // DRY_ADC (3500) → 0 %,  WET_ADC (800) → 100 %
    float range = (float)(SOIL_MOISTURE_DRY_ADC - SOIL_MOISTURE_WET_ADC);
    float offset = (float)(SOIL_MOISTURE_DRY_ADC - (int)r.soil_moisture_raw);
    r.soil_moisture_pct = constrain((offset / range) * 100.0f, 0.0f, 100.0f);

    // Probe open or shorted
    r.health_soil = (r.soil_moisture_raw < 10 || r.soil_moisture_raw > 4090)
                    ? SensorHealthState::DEGRADED
                    : SensorHealthState::ONLINE;

    // --- SW-420 Vibration ---
    // Interrupt count is accumulated by vibrationISR() between samples.
    // Read and reset atomically.
    noInterrupts();
    r.vibration_hits  = _vibrationCount;
    _vibrationCount   = 0;
    interrupts();

    r.health_vibration = SensorHealthState::ONLINE;
}

// ---------------------------------------------------------------------------
// Flame sensor
// ---------------------------------------------------------------------------
void SensorManager::readFlame(SensorReadings& r) {
    // Most modules: LOW = flame detected (Active LOW)
    r.flame_detected  = (digitalRead(PIN_FLAME_DIGITAL) == LOW);
    r.health_flame    = SensorHealthState::ONLINE;
}

// ---------------------------------------------------------------------------
// Diagnostics (Wi-Fi RSSI only — USB powered, no battery)
// ---------------------------------------------------------------------------
void SensorManager::readDiagnostics(SensorReadings& r) {
    r.wifi_rssi_dbm = (WiFi.status() == WL_CONNECTED) ? WiFi.RSSI() : -100;
}

// ---------------------------------------------------------------------------
// Water rate of rise helper
// ---------------------------------------------------------------------------
float SensorManager::calculateWaterRateOfRise(float current_cm, uint32_t now_ms) {
    uint32_t dt_ms = now_ms - _prev_water_time_ms;
    if (dt_ms < 2000) return 0.0f;  // Too fast — skip

    float delta_h   = current_cm - _prev_water_level_cm;
    float dt_min    = (float)dt_ms / 60000.0f;
    float rate      = delta_h / dt_min;

    _prev_water_level_cm = current_cm;
    _prev_water_time_ms  = now_ms;
    return rate;
}
