#include "alert_actuator.h"

AlertActuator::AlertActuator()
    : _last_buzzer_toggle_ms(0)
    , _buzzer_state(false)
    , _last_heartbeat_ms(0)
    , _heartbeat_state(false)
{
}

void AlertActuator::begin() {
    pinMode(PIN_BUZZER_2N2222A, OUTPUT);
    pinMode(PIN_LED_RED, OUTPUT);
    pinMode(PIN_LED_YELLOW, OUTPUT);
    pinMode(PIN_LED_GREEN, OUTPUT);

    // Initial safe states (All OFF)
    digitalWrite(PIN_BUZZER_2N2222A, LOW);
    digitalWrite(PIN_LED_RED, LOW);
    digitalWrite(PIN_LED_YELLOW, LOW);
    digitalWrite(PIN_LED_GREEN, LOW);
}

void AlertActuator::update(const HazardScores& scores) {
    applyLEDs(scores.highest_severity);
    applyBuzzer(scores.highest_severity);
}

void AlertActuator::applyLEDs(HazardSeverity sev) {
    uint32_t now = millis();

    switch (sev) {
        case HazardSeverity::CRITICAL:
            // Solid RED, Yellow/Green OFF
            digitalWrite(PIN_LED_RED, HIGH);
            digitalWrite(PIN_LED_YELLOW, LOW);
            digitalWrite(PIN_LED_GREEN, LOW);
            break;

        case HazardSeverity::WARNING:
            // Solid YELLOW, Red/Green OFF
            digitalWrite(PIN_LED_RED, LOW);
            digitalWrite(PIN_LED_YELLOW, HIGH);
            digitalWrite(PIN_LED_GREEN, LOW);
            break;

        case HazardSeverity::LOW:
            // Gentle Yellow pulse or Green
            digitalWrite(PIN_LED_RED, LOW);
            digitalWrite(PIN_LED_YELLOW, HIGH);
            digitalWrite(PIN_LED_GREEN, HIGH);
            break;

        case HazardSeverity::NORMAL:
        default:
            // Heartbeat Green pulse (1 Hz blink), Red & Yellow OFF
            digitalWrite(PIN_LED_RED, LOW);
            digitalWrite(PIN_LED_YELLOW, LOW);
            if (now - _last_heartbeat_ms >= HEARTBEAT_LED_INTERVAL_MS / 2) {
                _heartbeat_state = !_heartbeat_state;
                digitalWrite(PIN_LED_GREEN, _heartbeat_state ? HIGH : LOW);
                _last_heartbeat_ms = now;
            }
            break;
    }
}

void AlertActuator::applyBuzzer(HazardSeverity sev) {
    uint32_t now = millis();

    switch (sev) {
        case HazardSeverity::CRITICAL:
            // Rapid intermittent alarm: 150ms ON / 150ms OFF
            if (now - _last_buzzer_toggle_ms >= 150) {
                _buzzer_state = !_buzzer_state;
                digitalWrite(PIN_BUZZER_2N2222A, _buzzer_state ? HIGH : LOW);
                _last_buzzer_toggle_ms = now;
            }
            break;

        case HazardSeverity::WARNING:
            // Slow warning beep: 100ms chirp every 2 seconds
            if (now - _last_buzzer_toggle_ms >= 2000) {
                digitalWrite(PIN_BUZZER_2N2222A, HIGH);
                delay(80); // Brief safe synchronous chirp
                digitalWrite(PIN_BUZZER_2N2222A, LOW);
                _last_buzzer_toggle_ms = now;
            }
            break;

        case HazardSeverity::LOW:
        case HazardSeverity::NORMAL:
        default:
            // Silent
            digitalWrite(PIN_BUZZER_2N2222A, LOW);
            break;
    }
}
