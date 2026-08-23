#include "telemetry_network.h"
#include <WiFi.h>
#include <HTTPClient.h>

TelemetryNetwork::TelemetryNetwork(RingBuffer& buffer)
    : _ring_buffer(buffer)
    , _last_reconnect_attempt_ms(0)
    , _last_telemetry_sent_ms(0)
    , _is_connected(false)
{
}

void TelemetryNetwork::begin() {
    connectWiFi();
}

void TelemetryNetwork::connectWiFi() {
    Serial.printf("[WiFi] Connecting to SSID: %s ...\n", DEFAULT_WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.begin(DEFAULT_WIFI_SSID, DEFAULT_WIFI_PASS);
}

void TelemetryNetwork::loop() {
    uint32_t now = millis();

    // Check Wi-Fi state
    if (WiFi.status() == WL_CONNECTED) {
        if (!_is_connected) {
            _is_connected = true;
            Serial.printf("[WiFi] Connected! IP: %s, RSSI: %d dBm\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
            // Reconnected! Flush offline telemetry
            flushBufferedPackets();
        }
    } else {
        if (_is_connected) {
            _is_connected = false;
            Serial.println("[WiFi] Lost connection. Telemetry will buffer offline.");
        }
        // Attempt periodic reconnect every 10 seconds
        if (now - _last_reconnect_attempt_ms >= 10000) {
            _last_reconnect_attempt_ms = now;
            WiFi.reconnect();
        }
    }
}

bool TelemetryNetwork::isConnected() const {
    return _is_connected;
}

bool TelemetryNetwork::sendTelemetry(const TelemetryPacket& packet) {
    if (!_is_connected) {
        // Enqueue into offline ring buffer
        _ring_buffer.push(packet);
        Serial.printf("[Buffer] Offline. Packet #%u buffered (Total: %u)\n", packet.sequence_id, (unsigned int)_ring_buffer.count());
        return false;
    }

    bool ok = transmitJson(packet);
    if (!ok) {
        // Transmission failed (e.g. backend temporarily unreachable)
        _ring_buffer.push(packet);
        return false;
    }
    return true;
}

bool TelemetryNetwork::transmitJson(const TelemetryPacket& packet) {
    HTTPClient http;
    http.begin(BACKEND_HTTP_URL);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("Authorization", BACKEND_AUTH_TOKEN);
    http.setTimeout(2500);

    // Format JSON payload matching specification
    char json_buf[1024];
    snprintf(json_buf, sizeof(json_buf),
        "{"
        "\"node_id\":\"%s\","
        "\"firmware_version\":\"%s\","
        "\"sequence_id\":%u,"
        "\"location\":{\"latitude\":%0.4f,\"longitude\":%0.4f},"
        "\"temperature\":%0.2f,"
        "\"humidity\":%0.2f,"
        "\"pressure\":%0.2f,"
        "\"gas_resistance\":%0.1f,"
        "\"mq2_raw\":%u,"
        "\"mq7_raw\":%u,"
        "\"rain_raw\":%u,"
        "\"water_level_raw\":%u,"
        "\"water_level_cm\":%0.2f,"
        "\"water_rate_of_rise_cm_min\":%0.2f,"
        "\"flame_detected\":%s,"
        "\"battery_voltage\":%0.2f,"
        "\"signal_strength\":%d,"
        "\"sensor_health\":{"
            "\"bme680\":\"%s\","
            "\"dht22\":\"%s\","
            "\"mq2\":\"%s\","
            "\"mq7\":\"%s\","
            "\"rain\":\"%s\","
            "\"ultrasonic\":\"%s\","
            "\"water_probe\":\"%s\","
            "\"flame\":\"%s\""
        "},"
        "\"local_scores\":{"
            "\"flood\":%0.1f,"
            "\"fire\":%0.1f,"
            "\"pollution\":%0.1f"
        "}"
        "}",
        packet.node_id,
        packet.firmware_ver,
        packet.sequence_id,
        packet.latitude,
        packet.longitude,
        packet.readings.temperature_c,
        packet.readings.humidity_pct,
        packet.readings.pressure_hpa,
        packet.readings.gas_resistance_ohms,
        packet.readings.mq2_raw,
        packet.readings.mq7_raw,
        packet.readings.rain_raw,
        packet.readings.water_level_raw,
        packet.readings.water_level_cm,
        packet.readings.water_rate_of_rise_cm_min,
        packet.readings.flame_detected ? "true" : "false",
        packet.readings.battery_voltage,
        packet.readings.wifi_rssi_dbm,
        sensorHealthToString(packet.readings.health_bme680),
        sensorHealthToString(packet.readings.health_dht22),
        sensorHealthToString(packet.readings.health_mq2),
        sensorHealthToString(packet.readings.health_mq7),
        sensorHealthToString(packet.readings.health_rain),
        sensorHealthToString(packet.readings.health_ultrasonic),
        sensorHealthToString(packet.readings.health_water_probe),
        sensorHealthToString(packet.readings.health_flame),
        packet.scores.flood_score,
        packet.scores.fire_score,
        packet.scores.pollution_score
    );

    int http_code = http.POST(json_buf);
    http.end();

    if (http_code == 200 || http_code == 201) {
        return true;
    } else {
        Serial.printf("[HTTP] POST failed with code %d\n", http_code);
        return false;
    }
}

void TelemetryNetwork::flushBufferedPackets() {
    size_t count = _ring_buffer.count();
    if (count == 0) return;

    Serial.printf("[Sync] Flushing %u buffered telemetry packets to server...\n", (unsigned int)count);
    TelemetryPacket pkt;
    size_t flushed = 0;
    while (_ring_buffer.pop(pkt)) {
        if (!transmitJson(pkt)) {
            // Put it back if connection dropped midway
            _ring_buffer.push(pkt);
            break;
        }
        flushed++;
        delay(50); // Prevent network congestion
    }
    Serial.printf("[Sync] Successfully synchronized %u packets.\n", (unsigned int)flushed);
}
