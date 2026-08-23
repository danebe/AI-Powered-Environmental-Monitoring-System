#pragma once

#include "config.h"
#include "types.h"

class RingBuffer {
public:
    RingBuffer();
    bool push(const TelemetryPacket& packet);
    bool pop(TelemetryPacket& packet);
    bool peek(TelemetryPacket& packet) const;
    size_t count() const;
    bool isFull() const;
    bool isEmpty() const;
    void clear();

private:
    TelemetryPacket _buffer[TELEMETRY_RING_BUFFER_CAPACITY];
    size_t _head;
    size_t _tail;
    size_t _count;
};
