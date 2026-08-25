"""
Environmental Intelligence Network
High-Performance Unified Backend & Dashboard Server
"""

import http.server
import socketserver
import json
import time
import urllib.parse
import os
import threading
from typing import Dict, Any, List

import wave
import struct
import math


def ensure_sound_files(static_dir: str):
    sounds_dir = os.path.join(static_dir, "sounds")
    os.makedirs(sounds_dir, exist_ok=True)

    def create_wav(filename, duration, gen_fn):
        filepath = os.path.join(sounds_dir, filename)
        if os.path.exists(filepath):
            return
        sample_rate = 44100
        num_samples = int(duration * sample_rate)
        try:
            with wave.open(filepath, 'w') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                frames = bytearray()
                for i in range(num_samples):
                    t = float(i) / sample_rate
                    val = max(-1.0, min(1.0, gen_fn(t, duration)))
                    frames.extend(struct.pack('<h', int(val * 32767.0 * 0.45)))
                wav.writeframes(frames)
        except Exception:
            pass

    create_wav("eas_warning.wav", 1.5, lambda t, d: (math.sin(2.0 * math.pi * 853.0 * t) + math.sin(2.0 * math.pi * 960.0 * t)) * 0.5)
    create_wav("eas_flood.wav", 4.0, lambda t, d: (math.sin(2.0 * math.pi * 853.0 * t) + math.sin(2.0 * math.pi * 960.0 * t)) * 0.5 if t < 1.0 else math.sin(2.0 * math.pi * (480.0 + 220.0 * math.sin(2.0 * math.pi * 0.4 * (t - 1.0))) * t))
    create_wav("eas_fire.wav", 3.5, lambda t, d: (math.sin(2.0 * math.pi * 853.0 * t) + math.sin(2.0 * math.pi * 960.0 * t)) * 0.5 if t < 0.8 else math.sin(2.0 * math.pi * (1050.0 if int((t - 0.8)/0.15)%2==1 else 780.0) * t) * (0.6 + 0.4 * math.exp(-3.0 * ((t - 0.8) % 0.15))))
    create_wav("eas_gas.wav", 3.5, lambda t, d: (math.sin(2.0 * math.pi * 853.0 * t) + math.sin(2.0 * math.pi * 960.0 * t)) * 0.5 if t < 0.8 else (math.sin(2.0 * math.pi * 1400.0 * t) if ((t-0.8)%0.4)<0.15 else (math.sin(2.0 * math.pi * 1650.0 * t) if ((t-0.8)%0.4)<0.3 else 0.0)))


from .schemas import TelemetryPayload, Location, SensorHealth, SystemThresholds, AlertEvent
from .analytics.normalization import SensorNormalizer
from .analytics.anomaly_detector import NodeAnomalyDetector
from .analytics.fusion_engine import RiskFusionEngine
from .analytics.edge_ai_engine import EdgeAIPredictor
from .alerts.alert_engine import AlertEngine
from .notifications.notification_engine import NotificationEngine
from .nodes.node_manager import NodeManager
from .simulator.sim_engine import ScenarioSimulator
from .storage import StorageManager
from .hardware.serial_reader import SerialHardwareReader


class EnvironmentalServerEngine:
    def __init__(self, static_dir: str, db_path: str = "environmental_network.db"):
        self.static_dir = os.path.abspath(static_dir)
        ensure_sound_files(self.static_dir)
        self.storage = StorageManager(db_path)
        self.thresholds = SystemThresholds()
        self.fusion_engine = RiskFusionEngine(self.thresholds)
        self.alert_engine = AlertEngine(self.thresholds)
        self.notification_engine = NotificationEngine(self.alert_engine)
        self.node_manager = NodeManager()
        self.simulator = ScenarioSimulator()
        self.serial_reader = SerialHardwareReader(self)

        # Per-node anomaly detectors
        self.anomaly_detectors: Dict[str, NodeAnomalyDetector] = {
            "NODE_001": NodeAnomalyDetector("NODE_001"),
            "NODE_002": NodeAnomalyDetector("NODE_002"),
            "NODE_003": NodeAnomalyDetector("NODE_003"),
            "NODE_004": NodeAnomalyDetector("NODE_004"),
        }

        # Latest state per node
        self.latest_states: Dict[str, Dict[str, Any]] = {}
        self.simulation_running = True

        # Pre-seed initial state
        self._preseed_initial_state()

        # Start simulation background worker
        self.sim_thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self.sim_thread.start()

    def _preseed_initial_state(self):
        for node_id in ["NODE_001", "NODE_002", "NODE_003", "NODE_004"]:
            pkt = self.simulator.generate_next_packet(node_id)
            self.ingest_telemetry(pkt)

    def _simulation_loop(self):
        while self.simulation_running:
            try:
                for node_id in ["NODE_001", "NODE_002", "NODE_003", "NODE_004"]:
                    # If real hardware reader is currently feeding this node, let hardware take priority
                    if self.serial_reader.connected and self.serial_reader.port and node_id == "NODE_001":
                        if time.time() - self.serial_reader.last_packet_time < 5.0:
                            continue

                    if self.simulator.active_scenario == "NODE_OFFLINE" and node_id == self.simulator.target_node_id:
                        continue
                    if self.simulator.active_scenario == "WIFI_FAILURE" and node_id == self.simulator.target_node_id:
                        continue

                    pkt = self.simulator.generate_next_packet(node_id)
                    self.ingest_telemetry(pkt)

                time.sleep(1.0)
            except Exception:
                time.sleep(1.0)

    def ingest_telemetry(self, payload: TelemetryPayload) -> Dict[str, Any]:
        node_id = payload.node_id

        # 1. Normalization & Sanity Validation
        norm_data = SensorNormalizer.sanitize_and_normalize(payload)

        # 2. Anomaly Tracking (EMA, Rolling Std, Derivative)
        if node_id not in self.anomaly_detectors:
            self.anomaly_detectors[node_id] = NodeAnomalyDetector(node_id)
        stats = self.anomaly_detectors[node_id].process(norm_data, payload.timestamp)

        # 3. 7-Hazard Multi-Sensor Risk Fusion
        scores = self.fusion_engine.evaluate_node(norm_data, stats)

        # 4. Edge AI Inference Confidence Check
        edge_ai_meta = EdgeAIPredictor.evaluate_edge_inference(norm_data, scores.to_dict())

        # 5. Alert & Event Processing with Tier Routing
        active_events = self.alert_engine.process_node_scores(node_id, scores, norm_data, payload.timestamp)
        for evt in active_events:
            self.storage.store_alert(evt)

        # 6. Node Heartbeat & Status
        node_active_count = len([a for a in self.alert_engine.active_alerts.values() if a.node_id == node_id])
        self.node_manager.update_node_heartbeat(payload, scores, node_active_count)

        # 7. Database Persistence
        self.storage.store_telemetry(payload, scores)

        # 8. Update Latest State
        state = {
            "node_id": node_id,
            "timestamp": payload.timestamp,
            "timestamp_iso": payload.timestamp_iso,
            "readings": payload.to_dict(),
            "normalized": norm_data,
            "anomaly_stats": stats,
            "scores": scores.to_dict(),
            "edge_ai": edge_ai_meta
        }
        self.latest_states[node_id] = state
        return state

    def get_system_overview(self) -> Dict[str, Any]:
        nodes = self.node_manager.get_all_nodes()
        total_nodes = len(nodes)
        online_nodes = len([n for n in nodes if n["status"] == "ONLINE"])
        offline_nodes = len([n for n in nodes if n["status"] == "OFFLINE"])
        degraded_nodes = len([n for n in nodes if n["status"] == "DEGRADED"])

        active_alerts = self.alert_engine.get_active_alerts()
        critical_alerts = len([a for a in active_alerts if a["severity"] == "CRITICAL"])

        max_hazard_score = 0.0
        max_hazard_type = "NONE"
        for s in self.latest_states.values():
            sc = s["scores"]["highest_score"]
            if sc > max_hazard_score:
                max_hazard_score = sc
                max_hazard_type = s["scores"]["highest_hazard"]

        tier_summary = self.notification_engine.get_tier_summary()
        hardware_status = self.serial_reader.get_status()

        return {
            "total_nodes": total_nodes,
            "online_nodes": online_nodes,
            "offline_nodes": offline_nodes,
            "degraded_nodes": degraded_nodes,
            "active_alerts_count": len(active_alerts),
            "critical_alerts_count": critical_alerts,
            "highest_hazard_score": max_hazard_score,
            "highest_hazard_type": max_hazard_type,
            "active_scenario": self.simulator.active_scenario,
            "target_node": self.simulator.target_node_id,
            "notification_tiers": tier_summary,
            "hardware_status": hardware_status,
            "timestamp": time.time(),
            "nodes": nodes,
            "active_alerts": active_alerts,
            "latest_states": self.latest_states
        }

    def get_map_heatmap_data(self) -> List[Dict[str, Any]]:
        nodes = self.node_manager.get_all_nodes()
        map_points = []
        for n in nodes:
            nid = n["node_id"]
            st = self.latest_states.get(nid, {})
            sc = st.get("scores", {})
            loc = n.get("location", {})
            map_points.append({
                "node_id": nid,
                "name": n.get("name", nid),
                "zone_type": n.get("zone_type", "URBAN"),
                "status": n.get("status", "ONLINE"),
                "latitude": loc.get("latitude", 28.6139),
                "longitude": loc.get("longitude", 77.2090),
                "highest_score": sc.get("highest_score", 0.0),
                "highest_hazard": sc.get("highest_hazard", "NONE"),
                "highest_severity": sc.get("highest_severity", "NORMAL"),
                "scores": sc
            })
        return map_points


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    engine: EnvironmentalServerEngine = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=self.engine.static_dir, **kwargs)

    def _set_json_headers(self, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_json_headers(200)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # -------------------------------------------------------------
        # REST API Endpoints
        # -------------------------------------------------------------
        if path == "/api/overview":
            data = self.engine.get_system_overview()
            self._set_json_headers(200)
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        elif path == "/api/nodes":
            nodes = self.engine.node_manager.get_all_nodes()
            self._set_json_headers(200)
            self.wfile.write(json.dumps(nodes).encode("utf-8"))
            return

        elif path == "/api/telemetry/latest":
            self._set_json_headers(200)
            self.wfile.write(json.dumps(self.engine.latest_states).encode("utf-8"))
            return

        elif path == "/api/telemetry/history":
            node_id = query.get("node_id", ["NODE_001"])[0]
            limit = int(query.get("limit", [60])[0])
            history = self.engine.storage.get_recent_history(node_id, limit=limit)
            self._set_json_headers(200)
            self.wfile.write(json.dumps(history).encode("utf-8"))
            return

        elif path == "/api/telemetry/trends":
            node_id = query.get("node_id", ["NODE_001"])[0]
            hours = int(query.get("hours", [24])[0])
            trends = self.engine.storage.get_trend_analysis(node_id, hours=hours)
            self._set_json_headers(200)
            self.wfile.write(json.dumps(trends).encode("utf-8"))
            return

        elif path == "/api/alerts":
            alerts = self.engine.alert_engine.get_active_alerts()
            self._set_json_headers(200)
            self.wfile.write(json.dumps(alerts).encode("utf-8"))
            return

        elif path == "/api/alerts/history":
            limit = int(query.get("limit", [50])[0])
            history = self.engine.alert_engine.get_alert_history(limit=limit)
            self._set_json_headers(200)
            self.wfile.write(json.dumps(history).encode("utf-8"))
            return

        elif path == "/api/notifications":
            tier = query.get("tier", ["ALL"])[0]
            items = self.engine.notification_engine.get_notifications_by_tier(tier)
            self._set_json_headers(200)
            self.wfile.write(json.dumps({
                "tier": tier,
                "count": len(items),
                "summary": self.engine.notification_engine.get_tier_summary(),
                "notifications": items
            }).encode("utf-8"))
            return

        elif path == "/api/map/heatmap":
            data = self.engine.get_map_heatmap_data()
            self._set_json_headers(200)
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        elif path == "/api/hardware/status":
            status = self.engine.serial_reader.get_status()
            self._set_json_headers(200)
            self.wfile.write(json.dumps(status).encode("utf-8"))
            return

        elif path == "/api/hardware/ports":
            ports = SerialHardwareReader.list_available_ports()
            self._set_json_headers(200)
            self.wfile.write(json.dumps(ports).encode("utf-8"))
            return

        elif path == "/api/simulator/status":
            data = {
                "active_scenario": self.engine.simulator.active_scenario,
                "target_node": self.engine.simulator.target_node_id,
                "scenarios": self.engine.simulator.SCENARIOS
            }
            self._set_json_headers(200)
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        elif path == "/api/config":
            self._set_json_headers(200)
            self.wfile.write(json.dumps(self.engine.thresholds.to_dict()).encode("utf-8"))
            return

        elif path == "/api/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            try:
                while True:
                    overview = self.engine.get_system_overview()
                    sse_data = f"data: {json.dumps(overview)}\n\n"
                    self.wfile.write(sse_data.encode("utf-8"))
                    self.wfile.flush()
                    time.sleep(1.0)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, TimeoutError):
                return
            except Exception:
                return

        # Default static file handling from dashboard directory
        if path == "/" or path == "":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            req_data = json.loads(body)
        except Exception:
            req_data = {}

        if path in ("/api/telemetry", "/api/hardware/ingest"):
            try:
                node_id = req_data.get("node_id", "NODE_001")
                loc_data = req_data.get("location", {})
                location = Location(
                    latitude=float(loc_data.get("latitude", 28.6139)),
                    longitude=float(loc_data.get("longitude", 77.2090)),
                    altitude_m=float(loc_data.get("altitude_m", 216.0))
                )

                health_data = req_data.get("sensor_health", {})
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
                    sequence_id=int(req_data.get("sequence_id", 0)),
                    firmware_version=str(req_data.get("firmware_version", "v2.0.0-ein")),
                    location=location,
                    temperature=float(req_data.get("temperature", 25.0)),
                    humidity=float(req_data.get("humidity", 50.0)),
                    pressure=float(req_data.get("pressure", 1013.25)),
                    gas_resistance=float(req_data.get("gas_resistance", 120000.0)),
                    mq2_raw=int(req_data.get("mq2_raw", 300)),
                    mq7_raw=int(req_data.get("mq7_raw", 250)),
                    rain_raw=int(req_data.get("rain_raw", 3900)),
                    water_level_raw=int(req_data.get("water_level_raw", 100)),
                    water_level_cm=float(req_data.get("water_level_cm", 12.0)),
                    water_rate_of_rise_cm_min=float(req_data.get("water_rate_of_rise_cm_min", 0.0)),
                    soil_moisture_raw=int(req_data.get("soil_moisture_raw", 0)),
                    soil_moisture_pct=float(req_data.get("soil_moisture_pct", 30.0)),
                    vibration_hits=int(req_data.get("vibration_hits", 0)),
                    water_ph=float(req_data.get("water_ph", 7.0)),
                    water_turbidity_ntu=float(req_data.get("water_turbidity_ntu", 0.0)),
                    flame_detected=bool(req_data.get("flame_detected", False)),
                    signal_strength=int(req_data.get("signal_strength", -60)),
                    sensor_health=health,
                    local_scores=req_data.get("local_scores", None)
                )

                res = self.engine.ingest_telemetry(payload)
                self._set_json_headers(200)
                self.wfile.write(json.dumps({"status": "success", "processed": res}).encode("utf-8"))
            except Exception as e:
                self._set_json_headers(400)
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        elif path == "/api/simulator/scenario":
            scenario = req_data.get("scenario", "NORMAL")
            node_id = req_data.get("node_id", "NODE_001")
            ok = self.engine.simulator.set_scenario(scenario, node_id)
            self._set_json_headers(200 if ok else 400)
            self.wfile.write(json.dumps({
                "status": "success" if ok else "invalid_scenario",
                "active_scenario": scenario,
                "target_node": node_id
            }).encode("utf-8"))
            return

        elif path == "/api/alerts/ack":
            event_id = req_data.get("event_id", "")
            user = req_data.get("acknowledged_by", "Control Room Operator")
            ok = self.engine.alert_engine.acknowledge_alert(event_id, user)
            self._set_json_headers(200 if ok else 404)
            self.wfile.write(json.dumps({
                "status": "acknowledged" if ok else "not_found",
                "event_id": event_id
            }).encode("utf-8"))
            return

        elif path == "/api/hardware/connect":
            port = req_data.get("port", "COM3")
            baud = int(req_data.get("baud", 115200))
            ok = self.engine.serial_reader.start(port=port, baud=baud)
            self._set_json_headers(200 if ok else 400)
            self.wfile.write(json.dumps({
                "status": "connecting" if ok else "failed",
                "port": port,
                "error": self.engine.serial_reader.last_error
            }).encode("utf-8"))
            return

        elif path == "/api/hardware/disconnect":
            self.engine.serial_reader.stop()
            self._set_json_headers(200)
            self.wfile.write(json.dumps({"status": "disconnected"}).encode("utf-8"))
            return

        self._set_json_headers(404)
        self.wfile.write(json.dumps({"status": "endpoint_not_found"}).encode("utf-8"))


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def run_server(host: str = "0.0.0.0", port: int = 8000, static_dir: str = "./dashboard"):
    engine = EnvironmentalServerEngine(static_dir=static_dir)
    CustomHTTPRequestHandler.engine = engine

    server = ThreadedHTTPServer((host, port), CustomHTTPRequestHandler)
    print(f"\n=======================================================")
    print(f"  Environmental Intelligence Network (EIN)")
    print(f"  Server listening at: http://localhost:{port}")
    print(f"  Dashboard available at: http://localhost:{port}/")
    print(f"  REST API root: http://localhost:{port}/api/overview")
    print(f"  Real-time SSE Stream: http://localhost:{port}/api/stream")
    print(f"=======================================================\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        engine.simulation_running = False
        engine.serial_reader.stop()
        server.shutdown()
