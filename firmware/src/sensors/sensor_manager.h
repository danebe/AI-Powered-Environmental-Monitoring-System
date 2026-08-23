#pragma once

#include "config.h"
#include "types.h"

class SensorManager {
public:
    SensorManager();
    void begin();
    SensorReadings sampleAll();

private:
    // Sensor reading subroutines
    void readAtmospheric(SensorReadings& r);
    void readGasSensors(SensorReadings& r);
    void readHydrological(SensorReadings& r);
    void readFlame(SensorReadings& r);
    void readDiagnostics(SensorReadings& r);

    // Rate-of-change and smoothing filters
    float calculateWaterRateOfRise(float current_level_cm, uint32_t now_ms);
    float calculateTempRateOfRise(float current_temp_c, uint32_t now_ms);

    // Filter memory
    float _prev_water_level_cm;
    uint32_t _prev_water_time_ms;
    float _water_ema;

    float _prev_temp_c;
    uint32_t _prev_temp_time_ms;

    // Baselines for MQ sensors (running baseline)
    float _mq2_baseline;
    float _mq7_baseline;
    uint32_t _calibration_samples;
};
