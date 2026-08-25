#pragma once
#include "../types.h"

class SensorManager {
public:
    SensorManager();
    void begin();
    SensorReadings sampleAll();

private:
    void readAtmospheric(SensorReadings& r);
    void readGasSensors(SensorReadings& r);
    void readHydrological(SensorReadings& r);
    void readSoilAndVibration(SensorReadings& r);
    void readFlame(SensorReadings& r);
    void readDiagnostics(SensorReadings& r);

    float calculateWaterRateOfRise(float current_level_cm, uint32_t now_ms);

    // State memory
    float    _prev_water_level_cm;
    uint32_t _prev_water_time_ms;
    float    _water_ema;
    float    _prev_temp_c;
    uint32_t _prev_temp_time_ms;
    float    _mq2_baseline;
    float    _mq7_baseline;
    int      _calibration_samples;

    // Vibration interrupt counter (incremented by ISR)
    static volatile uint16_t _vibrationCount;
};
