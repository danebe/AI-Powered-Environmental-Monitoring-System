#include "telemetry_network.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include "../../config.h"

TelemetryNetwork::TelemetryNetwork(RingBuffer& buffer)
    : _ring_buffer(buffer)
    , _last_reconnect_attempt_ms(0)
    , _is_connected(false)
{}

void TelemetryNetwork::begin() {
    Serial.printf("[WiFi] Connecting to SSID: %s ...\n", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);

    uint32_t start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_CONNECT_TIMEOUT_MS) {
        delay(250);
        Serial.print(".");
    }
    Serial.println();

    if (WiFi.status() == WL_CONNECTED) {
        _is_connected = true;
        Serial.printf("[WiFi] Connected. IP: %s  RSSI: %d dBm\n",
                      WiFi.localIP().toString().c_str(), WiFi.RSSI());
    } else {
        Serial.println("[WiFi] Initial connect failed. Will retry in loop.");
    }
}

void TelemetryNetwork::loop() {
    uint32_t now = millis();

    if (WiFi.status() == WL_CONNECTED) {
        if (!_is_connected) {
            _is_connected = true;
            Serial.printf("[WiFi] Reconnected. IP: %s\n", WiFi.localIP().toString().c_str());
            flushBufferedPackets();
        }
    } else {
        if (_is_connected) {
            _is_connected = false;
            Serial.println("[WiFi] Connection lost. Buffering telemetry offline.");
        }
        if (now - _last_reconnect_attempt_ms >= 10000) {
            _last_reconnect_attempt_ms = now;
            WiFi.reconnect();
        }
    }
}

bool TelemetryNetwork::isConnected() const { return _is_connected; }

bool TelemetryNetwork::sendTelemetry(const TelemetryPacket& packet) {
    if (!_is_connected) {
        _ring_buffer.push(packet);
        Serial.printf("[Buffer] Offline. Packet #%u buffered (%u total)\n",
                      packet.sequence_id, (unsigned)_ring_buffer.count());
        return false;
    }
    bool ok = transmitJson(packet);
    if (!ok) {
        _ring_buffer.push(packet);
    }
    return ok;
}

bool TelemetryNetwork::transmitJson(const TelemetryPacket& p) {
    char url[128];
    snprintf(url, sizeof(url), "http://%s:%d%s", BACKEND_HOST, BACKEND_PORT, BACKEND_PATH);

    HTTPClient http;
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("Authorization", BACKEND_AUTH);
    http.setTimeout(2500);

    // Build JSON — includes all new sensor fields, no battery fields
    char buf[1536];
    snprintf(buf, sizeof(buf),
        "{"
        "\"node_id\":\"%s\","
        "\"firmware_version\":\"%s\","
        "\"sequence_id\":%u,"
        "\"location\":{\"latitude\":%.4f,\"longitude\":%.4f},"
        "\"temperature\":%.2f,"
        "\"humidity\":%.2f,"
        "\"pressure\":%.2f,"
        "\"gas_resistance\":%.1f,"
        "\"mq2_raw\":%u,"
        "\"mq7_raw\":%u,"
        "\"rain_raw\":%u,"
        "\"water_level_raw\":%u,"
        "\"water_level_cm\":%.2f,"
        "\"water_rate_of_rise_cm_min\":%.2f,"
        "\"soil_moisture_raw\":%u,"
        "\"soil_moisture_pct\":%.1f,"
        "\"vibration_hits\":%u,"
        "\"water_ph\":%.2f,"
        "\"water_turbidity_ntu\":%.1f,"
        "\"flame_detected\":%s,"
        "\"signal_strength\":%d,"
        "\"sensor_health\":{"
            "\"bme680\":\"%s\","
            "\"dht22\":\"%s\","
            "\"mq2\":\"%s\","
            "\"mq7\":\"%s\","
            "\"rain\":\"%s\","
            "\"ultrasonic\":\"%s\","
            "\"water_probe\":\"%s\","
            "\"flame\":\"%s\","
            "\"soil_moisture\":\"%s\","
            "\"vibration\":\"%s\""
        "},"
        "\"local_scores\":{"
            "\"flood\":%.1f,"
            "\"fire\":%.1f,"
            "\"pollution\":%.1f,"
            "\"heat\":%.1f,"
            "\"landslide\":%.1f,"
            "\"industrial\":%.1f,"
            "\"water_quality\":%.1f"
        "}"
        "}",
        p.node_id, p.firmware_ver, p.sequence_id,
        p.latitude, p.longitude,
        p.readings.temperature_c, p.readings.humidity_pct,
        p.readings.pressure_hpa,  p.readings.gas_resistance_ohms,
        p.readings.mq2_raw, p.readings.mq7_raw, p.readings.rain_raw,
        p.readings.water_level_raw, p.readings.water_level_cm,
        p.readings.water_rate_of_rise_cm_min,
        p.readings.soil_moisture_raw, p.readings.soil_moisture_pct,
        p.readings.vibration_hits,
        p.readings.water_ph, p.readings.water_turbidity_ntu,
        p.readings.flame_detected ? "true" : "false",
        p.readings.wifi_rssi_dbm,
        sensorHealthToString(p.readings.health_bme680),
        sensorHealthToString(p.readings.health_dht22),
        sensorHealthToString(p.readings.health_mq2),
        sensorHealthToString(p.readings.health_mq7),
        sensorHealthToString(p.readings.health_rain),
        sensorHealthToString(p.readings.health_ultrasonic),
        sensorHealthToString(p.readings.health_water_probe),
        sensorHealthToString(p.readings.health_flame),
        sensorHealthToString(p.readings.health_soil),
        sensorHealthToString(p.readings.health_vibration),
        p.scores.flood_score,      p.scores.fire_score,
        p.scores.pollution_score,  p.scores.heat_score,
        p.scores.landslide_score,  p.scores.industrial_score,
        p.scores.water_quality_score
    );

    // Also output newline-delimited JSON over USB Serial (for COM port / Web Serial dashboard link)
    Serial.println(buf);

    int code = http.POST(buf);
    http.end();

    if (code == 200 || code == 201) return true;
    Serial.printf("[HTTP] POST status: %d\n", code);
    return false;
}

void TelemetryNetwork::flushBufferedPackets() {
    size_t count = _ring_buffer.count();
    if (count == 0) return;
    Serial.printf("[Sync] Flushing %u buffered packets...\n", (unsigned)count);
    TelemetryPacket pkt;
    size_t flushed = 0;
    while (_ring_buffer.pop(pkt)) {
        if (!transmitJson(pkt)) { _ring_buffer.push(pkt); break; }
        flushed++;
        delay(50);
    }
    Serial.printf("[Sync] Flushed %u packets.\n", (unsigned)flushed);
}
