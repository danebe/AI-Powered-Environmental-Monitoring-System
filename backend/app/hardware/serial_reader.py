"""
Environmental Intelligence Network
Serial Hardware Reader for Physical ESP32 USB Connection
"""

import threading
import time
import json
from typing import Optional, Dict, Any

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False


class SerialHardwareReader:
    """
    Reads newline-delimited JSON telemetry from a USB-connected ESP32 edge node.
    Ingests live sensor data directly into the EnvironmentalServerEngine.
    """

    def __init__(self, engine, port: Optional[str] = None, baud: int = 115200):
        self.engine = engine
        self.port = port
        self.baud = baud
        self.serial_conn = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.packets_ingested = 0
        self.last_packet_time = 0.0
        self.last_error = "" if HAS_SERIAL else "pyserial not installed (pip install pyserial)"
        self.connected = False

    @staticmethod
    def list_available_ports() -> list:
        if not HAS_SERIAL:
            return []
        try:
            ports = serial.tools.list_ports.comports()
            return [{"port": p.device, "description": p.description} for p in ports]
        except Exception:
            return []

    def start(self, port: Optional[str] = None, baud: int = 115200) -> bool:
        if not HAS_SERIAL:
            self.last_error = "pyserial package not installed"
            return False

        if port:
            self.port = port
        if baud:
            self.baud = baud

        if not self.port:
            self.last_error = "No COM port specified"
            return False

        self.stop()
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        self.running = False
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except Exception:
                pass
            self.serial_conn = None
        self.connected = False

    def _read_loop(self):
        while self.running:
            try:
                if not self.serial_conn:
                    self.serial_conn = serial.Serial(self.port, self.baud, timeout=2.0)
                    self.connected = True
                    self.last_error = ""

                line = self.serial_conn.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                if line.startswith("{") and line.endswith("}"):
                    try:
                        data = json.loads(line)
                        node_id = data.get("node_id", "NODE_001")
                        from ..schemas import TelemetryPayload, Location, SensorHealth

                        loc_data = data.get("location", {})
                        location = Location(
                            latitude=float(loc_data.get("latitude", 28.6139)),
                            longitude=float(loc_data.get("longitude", 77.2090)),
                            altitude_m=float(loc_data.get("altitude_m", 216.0)),
                            zone_description=loc_data.get("zone_description", "Field Node")
                        )

                        health_data = data.get("sensor_health", {})
                        health = SensorHealth(
                            bme680=health_data.get("bme680", "ONLINE"),
                            dht22=health_data.get("dht22", "ONLINE"),
                            mq2=health_data.get("mq2", "ONLINE"),
                            mq7=health_data.get("mq7", "ONLINE"),
                            rain=health_data.get("rain", "ONLINE"),
                            ultrasonic=health_data.get("ultrasonic", "ONLINE"),
                            water_probe=health_data.get("water_probe", "ONLINE"),
                            flame=health_data.get("flame", "ONLINE"),
                            soil_moisture=health_data.get("soil_moisture", "ONLINE"),
                            vibration=health_data.get("vibration", "ONLINE")
                        )

                        payload = TelemetryPayload(
                            node_id=node_id,
                            timestamp=time.time(),
                            sequence_id=int(data.get("sequence_id", self.packets_ingested + 1)),
                            firmware_version=str(data.get("firmware_version", "v2.0.0-ein")),
                            location=location,
                            temperature=float(data.get("temperature", 25.0)),
                            humidity=float(data.get("humidity", 50.0)),
                            pressure=float(data.get("pressure", 1013.25)),
                            gas_resistance=float(data.get("gas_resistance", 120000.0)),
                            mq2_raw=int(data.get("mq2_raw", 300)),
                            mq7_raw=int(data.get("mq7_raw", 250)),
                            rain_raw=int(data.get("rain_raw", 3900)),
                            water_level_raw=int(data.get("water_level_raw", 100)),
                            water_level_cm=float(data.get("water_level_cm", 12.0)),
                            water_rate_of_rise_cm_min=float(data.get("water_rate_of_rise_cm_min", 0.0)),
                            soil_moisture_raw=int(data.get("soil_moisture_raw", 0)),
                            soil_moisture_pct=float(data.get("soil_moisture_pct", 30.0)),
                            vibration_hits=int(data.get("vibration_hits", 0)),
                            water_ph=float(data.get("water_ph", 7.0)),
                            water_turbidity_ntu=float(data.get("water_turbidity_ntu", 0.0)),
                            flame_detected=bool(data.get("flame_detected", False)),
                            signal_strength=int(data.get("signal_strength", -60)),
                            sensor_health=health,
                            local_scores=data.get("local_scores", None)
                        )

                        self.engine.ingest_telemetry(payload)
                        self.packets_ingested += 1
                        self.last_packet_time = time.time()
                    except Exception as parse_err:
                        self.last_error = f"JSON parse/ingest error: {parse_err}"

            except Exception as e:
                self.connected = False
                self.last_error = str(e)
                if self.serial_conn:
                    try:
                        self.serial_conn.close()
                    except Exception:
                        pass
                    self.serial_conn = None
                time.sleep(2.0)

    def get_status(self) -> Dict[str, Any]:
        return {
            "has_pyserial": HAS_SERIAL,
            "connected": self.connected,
            "port": self.port,
            "baud": self.baud,
            "packets_ingested": self.packets_ingested,
            "last_packet_time": self.last_packet_time,
            "last_error": self.last_error,
            "available_ports": self.list_available_ports()
        }
