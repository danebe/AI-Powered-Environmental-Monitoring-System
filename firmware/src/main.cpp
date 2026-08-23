/**
 * ============================================================================
 * SIH 2026 Resilient AI-Assisted Environmental Monitoring Network
 * Main Firmware Entry Point for ESP32 Edge Node
 * Target: ESP32-WROOM-32 (30-pin)
 * ============================================================================
 */

#include <Arduino.h>
#include "config.h"
#include "types.h"
#include "sensors/sensor_manager.h"
#include "fusion/local_fusion.h"
#include "actuators/alert_actuator.h"
#include "display/oled_display.h"
#include "storage/ring_buffer.h"
#include "network/telemetry_network.h"

// Core Module Instances
static SensorManager sensorMgr;
static LocalFusionEngine fusionEngine;
static AlertActuator alertActuator;
static OledDisplay oledDisplay;
static RingBuffer ringBuffer;
static TelemetryNetwork network(ringBuffer);

// Runtime State Variables
static uint32_t sequenceId = 0;
static uint32_t lastSampleMs = 0;
static uint32_t lastTelemetryMs = 0;

void setup() {
    Serial.begin(115200);
    delay(500);

    Serial.println("\n=======================================================");
    Serial.printf("  SIH 2026 Environmental Monitoring Node (%s)\n", NODE_ID);
    Serial.printf("  Firmware: %s\n", FIRMWARE_VERSION);
    Serial.println("=======================================================\n");

    // 1. Initialize hardware subsystems
    sensorMgr.begin();
    alertActuator.begin();
    oledDisplay.begin();
    network.begin();

    Serial.println("[System] All peripherals initialized. Entering real-time monitoring loop.");
}

void loop() {
    uint32_t now = millis();

    // 1. Maintain Network State & Buffered Sync
    network.loop();

    // 2. Periodic Sensor Sampling & Local Hazard Fusion (Every 1s)
    if (now - lastSampleMs >= SENSOR_READ_INTERVAL_MS) {
        lastSampleMs = now;

        // Sample raw and calibrated readings
        SensorReadings readings = sensorMgr.sampleAll();

        // Perform on-node deterministic sensor fusion (Safety Critical Offline Loop)
        HazardScores scores = fusionEngine.evaluate(readings);

        // Update local physical actuators (Buzzer 2N2222A + Tri-Color LEDs)
        alertActuator.update(scores);

        // Render to OLED Display
        oledDisplay.render(readings, scores);

        // 3. Periodic Telemetry Transmission to Backend (Every 3s)
        if (now - lastTelemetryMs >= TELEMETRY_SEND_INTERVAL_MS) {
            lastTelemetryMs = now;
            sequenceId++;

            TelemetryPacket packet;
            strncpy(packet.node_id, NODE_ID, sizeof(packet.node_id));
            strncpy(packet.firmware_ver, FIRMWARE_VERSION, sizeof(packet.firmware_ver));
            packet.sequence_id = sequenceId;
            packet.epoch_timestamp = now / 1000;
            packet.latitude = NODE_LATITUDE;
            packet.longitude = NODE_LONGITUDE;
            packet.readings = readings;
            packet.scores = scores;

            // Transmit over Wi-Fi (or buffer in RAM ring-buffer if disconnected)
            network.sendTelemetry(packet);
        }
    }

    // Small cooperative yield
    delay(10);
}
