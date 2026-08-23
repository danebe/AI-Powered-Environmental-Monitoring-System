#pragma once

#include "config.h"
#include "types.h"

class OledDisplay {
public:
    OledDisplay();
    void begin();
    void render(const SensorReadings& r, const HazardScores& scores);

private:
    void drawNormalScreen(const SensorReadings& r, const HazardScores& scores);
    void drawWarningScreen(const SensorReadings& r, const HazardScores& scores);
    void drawCriticalScreen(const SensorReadings& r, const HazardScores& scores);

    uint32_t _last_render_ms;
};
