#pragma once

#include "config.h"
#include "types.h"

class LocalFusionEngine {
public:
    LocalFusionEngine();
    HazardScores evaluate(const SensorReadings& r);

private:
    float computeFloodRisk(const SensorReadings& r, char* reason_out, size_t max_len);
    float computeFireRisk(const SensorReadings& r, char* reason_out, size_t max_len);
    float computePollutionRisk(const SensorReadings& r, char* reason_out, size_t max_len);

    HazardSeverity scoreToSeverity(float score);

    // Persistence counters for transient noise rejection
    uint8_t _consecutive_fire_spikes;
    uint8_t _consecutive_pollution_spikes;
};
