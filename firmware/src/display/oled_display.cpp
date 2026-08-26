#include "oled_display.h"
#include <Wire.h>
#include <Adafruit_GFX.h>

#if USE_SH1106_1_3_INCH
#include <Adafruit_SH110X.h>
static Adafruit_SH1106G display(OLED_SCREEN_WIDTH, OLED_SCREEN_HEIGHT, &Wire, -1);
#define COLOR_WHITE SH110X_WHITE
#define COLOR_BLACK SH110X_BLACK
#else
#include <Adafruit_SSD1306.h>
static Adafruit_SSD1306 display(OLED_SCREEN_WIDTH, OLED_SCREEN_HEIGHT, &Wire, -1);
#define COLOR_WHITE SSD1306_WHITE
#define COLOR_BLACK SSD1306_BLACK
#endif

OledDisplay::OledDisplay()
    : _last_render_ms(0)
    , _initialized(false)
{
}

void OledDisplay::begin() {
    #if USE_SH1106_1_3_INCH
    // Initialize SH1106 1.3" OLED Display (address usually 0x3C)
    if (display.begin(OLED_I2C_ADDRESS, true)) {
        _initialized = true;
        display.clearDisplay();
        display.setTextColor(COLOR_WHITE);
        display.setTextSize(1);
        display.setCursor(0, 0);
        display.println(F("SIH 2026 Node Init"));
        display.println(F("OLED: SH1106 1.3\""));
        display.printf("ID: %s\n", NODE_ID);
        display.display();
        Serial.println("[OLED] SH1106 1.3\" I2C display initialized successfully.");
    } else {
        Serial.println("[OLED] WARNING: SH1106 OLED initialization failed at 0x3C.");
    }
    #else
    // Initialize SSD1306 0.96" OLED Display
    if (display.begin(SSD1306_SWITCHCAPVCC, OLED_I2C_ADDRESS)) {
        _initialized = true;
        display.clearDisplay();
        display.setTextColor(COLOR_WHITE);
        display.setTextSize(1);
        display.setCursor(0, 0);
        display.println(F("SIH 2026 Node Init"));
        display.println(F("OLED: SSD1306 0.96\""));
        display.printf("ID: %s\n", NODE_ID);
        display.display();
        Serial.println("[OLED] SSD1306 0.96\" I2C display initialized successfully.");
    } else {
        Serial.println("[OLED] WARNING: SSD1306 OLED initialization failed at 0x3C.");
    }
    #endif
}

void OledDisplay::render(const SensorReadings& r, const HazardScores& scores) {
    if (!_initialized) return;

    uint32_t now = millis();
    if (now - _last_render_ms < OLED_REFRESH_INTERVAL_MS) {
        return;
    }
    _last_render_ms = now;

    switch (scores.highest_severity) {
        case HazardSeverity::CRITICAL:
            drawCriticalScreen(r, scores);
            break;
        case HazardSeverity::WARNING:
            drawWarningScreen(r, scores);
            break;
        case HazardSeverity::LOW:
        case HazardSeverity::NORMAL:
        default:
            drawNormalScreen(r, scores);
            break;
    }
}

void OledDisplay::drawNormalScreen(const SensorReadings& r, const HazardScores& scores) {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(COLOR_WHITE);
    
    // Header Bar
    display.setCursor(0, 0);
    display.printf("%s [NORMAL]", NODE_ID);
    display.drawLine(0, 9, 127, 9, COLOR_WHITE);

    // Sensor Readings Grid
    display.setCursor(0, 13);
    display.printf("T: %0.1fC   H: %0.0f%%\n", r.temperature_c, r.humidity_pct);
    display.printf("P: %0.0f hPa\n", r.pressure_hpa);
    display.printf("Water: %0.1f cm\n", r.water_level_cm);
    display.printf("Soil: %0.0f%%  Vib: %u\n", r.soil_moisture_pct, r.vibration_hits);
    display.printf("Peak Risk: %0.0f/100\n", scores.highest_score);
    display.display();
}

void OledDisplay::drawWarningScreen(const SensorReadings& r, const HazardScores& scores) {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(COLOR_WHITE);

    // Inverted header for warning
    display.fillRect(0, 0, 128, 10, COLOR_WHITE);
    display.setTextColor(COLOR_BLACK, COLOR_WHITE);
    display.setCursor(2, 1);
    display.printf("! WARNING: %s !", hazardTypeToString(scores.highest_hazard));
    display.setTextColor(COLOR_WHITE, COLOR_BLACK);

    display.setCursor(0, 13);
    display.printf("Risk Score: %0.0f/100\n", scores.highest_score);
    
    if (scores.highest_hazard == HazardType::FLOOD) {
        display.printf("Water: %0.1f cm (+%0.1f)\n", r.water_level_cm, r.water_rate_of_rise_cm_min);
        display.printf("Rain Intensity: %0.0f%%\n", r.rain_intensity_pct);
    } else if (scores.highest_hazard == HazardType::LANDSLIDE) {
        display.printf("Soil Sat: %0.0f%%\n", r.soil_moisture_pct);
        display.printf("Vibration: %u hits/s\n", r.vibration_hits);
    } else if (scores.highest_hazard == HazardType::FIRE || scores.highest_hazard == HazardType::HEAT) {
        display.printf("Temp: %0.1f C\n", r.temperature_c);
        display.printf("Smoke: %0.0f%%  CO: %0.0f%%\n", r.mq2_anomaly_idx, r.mq7_anomaly_idx);
    } else {
        display.printf("Gas Res: %0.0f kO\n", r.gas_resistance_ohms / 1000.0f);
        display.printf("CO: %0.0f%%  Smoke: %0.0f%%\n", r.mq7_anomaly_idx, r.mq2_anomaly_idx);
    }
    display.println(F("Status: MONITORING"));
    display.display();
}

void OledDisplay::drawCriticalScreen(const SensorReadings& r, const HazardScores& scores) {
    display.clearDisplay();
    display.setTextSize(1);

    // Blinking inverted banner
    bool blink = (millis() / 500) % 2 == 0;
    if (blink) {
        display.fillRect(0, 0, 128, 12, COLOR_WHITE);
        display.setTextColor(COLOR_BLACK, COLOR_WHITE);
    } else {
        display.drawRect(0, 0, 128, 12, COLOR_WHITE);
        display.setTextColor(COLOR_WHITE, COLOR_BLACK);
    }
    
    display.setCursor(2, 2);
    display.printf("!! CRITICAL %s !!", hazardTypeToString(scores.highest_hazard));
    display.setTextColor(COLOR_WHITE, COLOR_BLACK);

    display.setCursor(0, 15);
    display.printf("RISK INDEX: %0.0f / 100\n", scores.highest_score);
    
    if (scores.highest_hazard == HazardType::FLOOD) {
        display.printf("Depth: %0.1fcm  Surge: +%0.1f\n", r.water_level_cm, r.water_rate_of_rise_cm_min);
        display.println(F("EVACUATE LOW GROUND"));
    } else if (scores.highest_hazard == HazardType::LANDSLIDE) {
        display.printf("Soil: %0.0f%%  Vib: %u/s\n", r.soil_moisture_pct, r.vibration_hits);
        display.println(F("SLOPE SLIP DANGER"));
    } else if (scores.highest_hazard == HazardType::FIRE) {
        display.printf("T: %0.1fC Smoke: %0.0f%%\n", r.temperature_c, r.mq2_anomaly_idx);
        if (r.flame_detected) display.println(F("FLAME CONFIRMED!"));
        else display.println(F("WILDFIRE THREAT"));
    } else {
        display.printf("CO: %0.0f%%  VOC: %0.0fkO\n", r.mq7_anomaly_idx, r.gas_resistance_ohms / 1000.0f);
        display.println(F("TOXIC PLUME HAZARD"));
    }
    display.display();
}
