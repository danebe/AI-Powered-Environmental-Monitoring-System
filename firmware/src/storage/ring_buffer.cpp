#include "ring_buffer.h"

RingBuffer::RingBuffer()
    : _head(0)
    , _tail(0)
    , _count(0)
{
}

bool RingBuffer::push(const TelemetryPacket& packet) {
    _buffer[_head] = packet;
    _head = (_head + 1) % TELEMETRY_RING_BUFFER_CAPACITY;

    if (_count < TELEMETRY_RING_BUFFER_CAPACITY) {
        _count++;
    } else {
        // Buffer full: overwrite oldest item (advance tail)
        _tail = (_tail + 1) % TELEMETRY_RING_BUFFER_CAPACITY;
    }
    return true;
}

bool RingBuffer::pop(TelemetryPacket& packet) {
    if (_count == 0) {
        return false;
    }
    packet = _buffer[_tail];
    _tail = (_tail + 1) % TELEMETRY_RING_BUFFER_CAPACITY;
    _count--;
    return true;
}

bool RingBuffer::peek(TelemetryPacket& packet) const {
    if (_count == 0) {
        return false;
    }
    packet = _buffer[_tail];
    return true;
}

size_t RingBuffer::count() const {
    return _count;
}

bool RingBuffer::isFull() const {
    return _count >= TELEMETRY_RING_BUFFER_CAPACITY;
}

bool RingBuffer::isEmpty() const {
    return _count == 0;
}

void RingBuffer::clear() {
    _head = 0;
    _tail = 0;
    _count = 0;
}
