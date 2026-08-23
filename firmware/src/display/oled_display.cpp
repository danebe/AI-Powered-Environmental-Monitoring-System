#include "oled_display.h"
#include <Wire.h>

// When building on hardware with Adafruit_SSD1306:
// #include <Adafruit_GFX.h>
// #include <Adafruit_SSD1306.h>
// static Adafruit_SSD1306 display(OLED_SCREEN_WIDTH, OLED_SCREEN_HEIGHT, &Wire, -1);

OledDisplay::OledDisplay()
    : _last_render_ms(0)
{
}

void OledDisplay::begin() {
    // In production build:
    // display.begin(SSD1306_SWITCHCAPVCC, OLED_I2C_ADDRESS);
    // display.clearDisplay();
    // display.setTextColor(SSD1306_WHITE);
    // display.setTextSize(1);
    // display.setCursor(0, 0);
    // display.println(F("SIH 2026 Node Init"));
    // display.display();
}

void OledDisplay::render(const SensorReadings& r, const HazardScores& scores) {
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
    // Formats:
    // ENVIRONMENT NORMAL
    // T: 28.4 C
    // H: 72 %
    // Flood: LOW
    // Fire: LOW
    /*
    display.clearDisplay();
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println(F("ENVIRONMENT NORMAL"));
    display.drawLine(0, 10, 127, 10, SSD1306_WHITE);

    display.setCursor(0, 16);
    display.printf("T: %0.1f C   P: %0.0f\n", r.temperature_c, r.pressure_hpa);
    display.printf("H: %0.0f %%\n", r.humidity_pct);
    display.printf("Flood: %s (%0.0f)\n", severityToString(scores.flood_severity), scores.flood_score);
    display.printf("Fire:  %s (%0.0f)\n", severityToString(scores.fire_severity), scores.fire_score);
    display.display();
    */
}

void OledDisplay::drawWarningScreen(const SensorReadings& r, const HazardScores& scores) {
    // Formats:
    // WARNING
    // FLOOD RISK: 68
    // Water: 42 cm
    // Rain: HIGH
    /*
    display.clearDisplay();
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println(F("--- WARNING ---"));
    display.drawLine(0, 10, 127, 10, SSD1306_WHITE);

    display.setCursor(0, 16);
    if (scores.flood_severity >= HazardSeverity::WARNING) {
        display.printf("FLOOD RISK: %0.0f\n", scores.flood_score);
        display.printf("Water: %0.1f cm\n", r.water_level_cm);
        display.printf("Rain:  %0.0f %%\n", r.rain_intensity_pct);
        display.printf("dWater: +%0.1f/m\n", r.water_rate_of_rise_cm_min);
    } else if (scores.fire_severity >= HazardSeverity::WARNING) {
        display.printf("FIRE RISK: %0.0f\n", scores.fire_score);
        display.printf("Temp:  %0.1f C\n", r.temperature_c);
        display.printf("Smoke: %0.0f %%\n", r.mq2_anomaly_idx);
        display.printf("CO:    %0.0f %%\n", r.mq7_anomaly_idx);
    } else {
        display.printf("POLLUTION: %0.0f\n", scores.pollution_score);
        display.printf("CO idx:   %0.0f %%\n", r.mq7_anomaly_idx);
        display.printf("VOC res:  %0.0f kO\n", r.gas_resistance_ohms / 1000.0f);
    }
    display.display();
    */
}

void OledDisplay::drawCriticalScreen(const SensorReadings& r, const HazardScores& scores) {
    // Formats:
    // !!! FLOOD ALERT !!!
    // Risk: 91
    // Water Rising
    // or:
    // !!! FIRE ALERT !!!
    // Risk: 88
    // Smoke Detected
    /*
    display.clearDisplay();
    display.setTextSize(1);
    display.setCursor(0, 0);
    if (scores.flood_severity == HazardSeverity::CRITICAL) {
        display.println(F("! CRITICAL FLOOD !"));
        display.drawLine(0, 10, 127, 10, SSD1306_WHITE);
        display.setCursor(0, 16);
        display.printf("Risk:  %0.0f / 100\n", scores.flood_score);
        display.printf("Depth: %0.1f cm\n", r.water_level_cm);
        display.printf("Surge: +%0.1f cm/m\n", r.water_rate_of_rise_cm_min);
        display.println(F("EVACUATE LOW GROUND"));
    } else if (scores.fire_severity == HazardSeverity::CRITICAL) {
        display.println(F("! CRITICAL FIRE !"));
        display.drawLine(0, 10, 127, 10, SSD1306_WHITE);
        display.setCursor(0, 16);
        display.printf("Risk:  %0.0f / 100\n", scores.fire_score);
        if (r.flame_detected) display.println(F("FLAME DETECTED!"));
        display.printf("Smoke: %0.0f %% | CO: %0.0f\n", r.mq2_anomaly_idx, r.mq7_anomaly_idx);
        display.printf("Temp:  %0.1f C\n", r.temperature_c);
    } else {
        display.println(F("! HAZARD ALERT !"));
        display.drawLine(0, 10, 127, 10, SSD1306_WHITE);
        display.setCursor(0, 16);
        display.printf("Pollution: %0.0f\n", scores.pollution_score);
        display.println(scores.primary_alert_detail);
    }
    display.display();
    */
}
