# ESP32 Edge Node Firmware - SIH 2026

## Target Hardware
* **Board:** ESP32-WROOM-32 (30-Pin NodeMCU / DevKit V1)
* **Power:** USB 5V (Development) / 3.7V Li-ion + Buck Converter (Field Deployment)

---

## 30-Pin ESP32 Wiring Diagram

| ESP32 Pin | Component | Module Pin | Purpose / Notes |
|:---|:---|:---|:---|
| **GPIO21** | BME680 + OLED Display | `SDA` | I2C Data bus (shared) |
| **GPIO22** | BME680 + OLED Display | `SCL` | I2C Clock bus (shared) |
| **GPIO19** | DHT22 | `DATA` | Temperature & Relative Humidity backup |
| **GPIO34** | MQ-2 Gas Sensor | `AOUT` | Smoke & combustible gas analog signal (Input Only ADC1) |
| **GPIO35** | MQ-7 Gas Sensor | `AOUT` | Carbon Monoxide (CO) analog signal (Input Only ADC1) |
| **GPIO33** | FC-37 Rain Sensor | `AOUT` | Rain droplet conductivity proxy |
| **GPIO32** | Water Level Sensor | `SIG` | Conductive water immersion sensor |
| **GPIO39** | FC-28 Soil Moisture | `AOUT` | Soil moisture / saturation analog signal (Input Only ADC1) |
| **GPIO23** | SW-420 Vibration | `DOUT` | Digital ground tremor / slope vibration pulse |
| **GPIO5** | HC-SR04 Ultrasonic | `TRIG` | Ultrasonic pulse trigger |
| **GPIO18** | HC-SR04 Ultrasonic | `ECHO` | Ultrasonic echo pulse input (Use 1k/2k voltage divider if 5V module) |
| **GPIO25** | Flame Sensor | `DOUT` | Digital optical flame/IR detection |
| **GPIO26** | 2N2222A Transistor Base | `1kΩ Base Resistor` | Active Buzzer driver (Collector to Buzzer -, Emitter to GND) |
| **GPIO27** | Red LED | `Anode (via 220Ω)` | Critical Alert Indicator |
| **GPIO14** | Yellow LED | `Anode (via 220Ω)` | Warning Alert Indicator |
| **GPIO13** | Green LED | `Anode (via 220Ω)` | Normal Status & Heartbeat Pulse |
| **3V3** | BME680, OLED, DHT22, Flame, FC-28 | `VCC` | 3.3V Power rail |
| **VIN / 5V** | MQ-2, MQ-7, HC-SR04, SW-420 | `VCC` | 5V Power rail (from USB) |
| **GND** | All sensors & modules | `GND` | Common Ground Plane |

> [!NOTE]
> * **1.3" I2C OLED Driver:** 1.3" OLEDs use the **SH1106** controller chip. This is configured in `include/config.h` (`#define USE_SH1106_1_3_INCH 1`). If using a 0.96" OLED (SSD1306), change this define to `0`.
> * GPIO34, GPIO35, and GPIO39 are input-only ADC pins on the ESP32 and do not support output or software pull-ups.

---

## How to Build & Flash
1. Open Visual Studio Code with the **PlatformIO IDE** extension installed.
2. Open the `firmware` folder.
3. Edit `include/config.h` to set your local Wi-Fi SSID, password, and backend server IP.
4. Connect the ESP32 via micro-USB and click **Upload** (or run `pio run -t upload --upload-port COM6`).
5. Open Serial Monitor at `115200` baud to observe live edge telemetry and sensor fusion diagnostics.
