#pragma once
#include "../../types.h"
#include "../../config.h"

class LocalFusionEngine {
public:
    LocalFusionEngine();
    HazardScores evaluate(const SensorReadings& r);

private:
    HazardSeverity scoreToSeverity(float score);

    float computeFloodRisk(const SensorReadings& r, char* out, size_t n);
    float computeFireRisk(const SensorReadings& r, char* out, size_t n);
    float computePollutionRisk(const SensorReadings& r, char* out, size_t n);
    float computeHeatRisk(const SensorReadings& r, char* out, size_t n);
    float computeLandslideRisk(const SensorReadings& r, char* out, size_t n);

    int _consecutive_fire_spikes;
    int _consecutive_pollution_spikes;
    int _consecutive_landslide_spikes;
};
