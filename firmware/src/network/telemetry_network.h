#pragma once

#include "config.h"
#include "types.h"
#include "../storage/ring_buffer.h"

class TelemetryNetwork {
public:
    TelemetryNetwork(RingBuffer& buffer);
    void begin();
    void loop();
    bool sendTelemetry(const TelemetryPacket& packet);
    bool isConnected() const;

private:
    void connectWiFi();
    bool transmitJson(const TelemetryPacket& packet);
    void flushBufferedPackets();

    RingBuffer& _ring_buffer;
    uint32_t _last_reconnect_attempt_ms;
    uint32_t _last_telemetry_sent_ms;
    bool _is_connected;
};
