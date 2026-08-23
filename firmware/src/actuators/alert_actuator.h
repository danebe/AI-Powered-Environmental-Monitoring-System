#pragma once

#include "config.h"
#include "types.h"

class AlertActuator {
public:
    AlertActuator();
    void begin();
    void update(const HazardScores& scores);

private:
    void applyLEDs(HazardSeverity sev);
    void applyBuzzer(HazardSeverity sev);

    uint32_t _last_buzzer_toggle_ms;
    bool _buzzer_state;
    uint32_t _last_heartbeat_ms;
    bool _heartbeat_state;
};
