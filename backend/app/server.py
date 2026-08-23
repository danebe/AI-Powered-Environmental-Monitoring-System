"""
SIH 2026 Environmental Monitoring Network
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
from .alerts.alert_engine import AlertEngine
from .nodes.node_manager import NodeManager
from .simulator.sim_engine import ScenarioSimulator
from .storage import StorageManager


class EnvironmentalServerEngine:
    def __init__(self, static_dir: str, db_path: str = "environmental_network.db"):
        self.static_dir = os.path.abspath(static_dir)
        ensure_sound_files(self.static_dir)
        self.storage = StorageManager(db_path)
        self.thresholds = SystemThresholds()
        self.fusion_engine = RiskFusionEngine(self.thresholds)
        self.alert_engine = AlertEngine(self.thresholds)
        self.node_manager = NodeManager()
        self.simulator = ScenarioSimulator()

        # Per-node anomaly detectors
        self.anomaly_detectors: Dict[str, NodeAnomalyDetector] = {
            "NODE_001": NodeAnomalyDetector("NODE_001"),
            "NODE_002": NodeAnomalyDetector("NODE_002"),
            "NODE_003": NodeAnomalyDetector("NODE_003"),
            "NODE_004": NodeAnomalyDetector("NODE_004"),
        }

        # Latest processed state per node
        self.latest_states: Dict[str, Dict[str, Any]] = {}
        self.simulation_running = True

        # Pre-seed initial state for all nodes
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
                    if self.simulator.active_scenario == "NODE_OFFLINE" and node_id == self.simulator.target_node_id:
                        continue
                    if self.simulator.active_scenario == "WIFI_FAILURE" and node_id == self.simulator.target_node_id:
                        continue

                    pkt = self.simulator.generate_next_packet(node_id)
                    self.ingest_telemetry(pkt)

                time.sleep(1.0)
            except Exception as e:
                time.sleep(1.0)

    def ingest_telemetry(self, payload: TelemetryPayload) -> Dict[str, Any]:
        node_id = payload.node_id

        # 1. Normalization & Sanity Validation
        norm_data = SensorNormalizer.sanitize_and_normalize(payload)

        # 2. Anomaly Tracking (EMA, Rolling Std, Rate of Change)
        if node_id not in self.anomaly_detectors:
            self.anomaly_detectors[node_id] = NodeAnomalyDetector(node_id)
        stats = self.anomaly_detectors[node_id].process(norm_data, payload.timestamp)

        # 3. Multi-Sensor Hazard Fusion & Explainability
        scores = self.fusion_engine.evaluate_node(norm_data, stats)

        # 4. Alert & Event Processing
        active_events = self.alert_engine.process_node_scores(node_id, scores, norm_data, payload.timestamp)
        for evt in active_events:
            self.storage.store_alert(evt)

        # 5. Node Heartbeat & Status
        node_active_count = len([a for a in self.alert_engine.active_alerts.values() if a.node_id == node_id])
        self.node_manager.update_node_heartbeat(payload, scores, node_active_count)

        # 6. Database Storage & Memory Cache
        self.storage.store_telemetry(payload, scores)

        # 7. Update latest state
        state = {
            "node_id": node_id,
            "timestamp": payload.timestamp,
            "timestamp_iso": payload.timestamp_iso,
            "readings": payload.to_dict(),
            "normalized": norm_data,
            "anomaly_stats": stats,
            "scores": scores.to_dict()
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
            "timestamp": time.time(),
            "nodes": nodes,
            "active_alerts": active_alerts,
            "latest_states": self.latest_states
        }


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
            # Server-Sent Events (SSE) Real-Time Live Feed
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
                # Normal client browser refresh/disconnect
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

        if path == "/api/telemetry":
            try:
                node_id = req_data.get("node_id", "NODE_001")
                payload = TelemetryPayload(
                    node_id=node_id,
                    timestamp=time.time(),
                    sequence_id=req_data.get("sequence_id", 0),
                    firmware_version=req_data.get("firmware_version", "v1.4.0-sih2026"),
                    temperature=float(req_data.get("temperature", 25.0)),
                    humidity=float(req_data.get("humidity", 50.0)),
                    pressure=float(req_data.get("pressure", 1013.25)),
                    gas_resistance=float(req_data.get("gas_resistance", 120000.0)),
                    mq2_raw=int(req_data.get("mq2_raw", 300)),
                    mq7_raw=int(req_data.get("mq7_raw", 250)),
                    rain_raw=int(req_data.get("rain_raw", 4000)),
                    water_level_raw=int(req_data.get("water_level_raw", 0)),
                    water_level_cm=float(req_data.get("water_level_cm", 0.0)),
                    water_rate_of_rise_cm_min=float(req_data.get("water_rate_of_rise_cm_min", 0.0)),
                    flame_detected=bool(req_data.get("flame_detected", False)),
                    battery_voltage=float(req_data.get("battery_voltage", 3.8)),
                    signal_strength=int(req_data.get("signal_strength", -65))
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
            self.wfile.write(json.dumps({"status": "success" if ok else "invalid_scenario", "active_scenario": scenario, "target_node": node_id}).encode("utf-8"))
            return

        elif path == "/api/alerts/ack":
            event_id = req_data.get("event_id", "")
            user = req_data.get("acknowledged_by", "Control Room Operator")
            ok = self.engine.alert_engine.acknowledge_alert(event_id, user)
            self._set_json_headers(200 if ok else 404)
            self.wfile.write(json.dumps({"status": "acknowledged" if ok else "not_found", "event_id": event_id}).encode("utf-8"))
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
    print(f"  Environmental Monitoring Command Center")
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
        server.shutdown()
