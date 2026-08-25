"""
Environmental Intelligence Network
Storage Layer: SQLite Database and Fast In-Memory Cache
"""

import sqlite3
import json
import time
from typing import Dict, Any, List, Optional
from .schemas import TelemetryPayload, HazardScoreBreakdown, AlertEvent


class StorageManager:
    """
    Handles SQLite database persistence for long-term time-series history and alert records,
    plus in-memory caching for instant real-time queries.
    """

    def __init__(self, db_path: str = "environmental_network.db"):
        self.db_path = db_path
        self._init_db()
        self.recent_telemetry: Dict[str, List[Dict[str, Any]]] = {
            "NODE_001": [],
            "NODE_002": [],
            "NODE_003": [],
            "NODE_004": []
        }

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Telemetry records table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                timestamp_iso TEXT,
                temperature REAL,
                humidity REAL,
                pressure REAL,
                gas_resistance REAL,
                mq2_raw INTEGER,
                mq7_raw INTEGER,
                rain_raw INTEGER,
                water_level_cm REAL,
                water_rate_of_rise REAL,
                soil_moisture_pct REAL,
                vibration_hits INTEGER,
                water_ph REAL,
                water_turbidity_ntu REAL,
                flame_detected INTEGER,
                signal_strength INTEGER,
                flood_score REAL,
                fire_score REAL,
                pollution_score REAL,
                heat_score REAL,
                landslide_score REAL,
                industrial_score REAL,
                water_quality_score REAL,
                highest_severity TEXT,
                payload_json TEXT
            )
        """)

        # Alert history table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                event_id TEXT PRIMARY KEY,
                node_id TEXT NOT NULL,
                hazard_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                score REAL NOT NULL,
                timestamp REAL NOT NULL,
                timestamp_iso TEXT,
                title TEXT,
                reasons_json TEXT,
                sensor_evidence_json TEXT,
                notification_tier TEXT DEFAULT 'CITIZEN',
                acknowledged INTEGER DEFAULT 0,
                acknowledged_by TEXT
            )
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_node_time ON telemetry(node_id, timestamp)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_time ON alerts(timestamp)")

        conn.commit()
        conn.close()

    def store_telemetry(self, payload: TelemetryPayload, scores: HazardScoreBreakdown):
        data = payload.to_dict()
        data["scores"] = scores.to_dict()

        # 1. Update in-memory ring buffer (keep last 120 points per node)
        node_cache = self.recent_telemetry.setdefault(payload.node_id, [])
        node_cache.append(data)
        if len(node_cache) > 120:
            node_cache.pop(0)

        # 2. Persist to SQLite
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO telemetry (
                    node_id, timestamp, timestamp_iso, temperature, humidity, pressure,
                    gas_resistance, mq2_raw, mq7_raw, rain_raw, water_level_cm,
                    water_rate_of_rise, soil_moisture_pct, vibration_hits, water_ph,
                    water_turbidity_ntu, flame_detected, signal_strength,
                    flood_score, fire_score, pollution_score, heat_score,
                    landslide_score, industrial_score, water_quality_score,
                    highest_severity, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payload.node_id,
                payload.timestamp,
                payload.timestamp_iso,
                payload.temperature,
                payload.humidity,
                payload.pressure,
                payload.gas_resistance,
                payload.mq2_raw,
                payload.mq7_raw,
                payload.rain_raw,
                payload.water_level_cm,
                payload.water_rate_of_rise_cm_min,
                payload.soil_moisture_pct,
                payload.vibration_hits,
                payload.water_ph,
                payload.water_turbidity_ntu,
                1 if payload.flame_detected else 0,
                payload.signal_strength,
                scores.flood_score,
                scores.fire_score,
                scores.pollution_score,
                scores.heat_score,
                scores.landslide_score,
                scores.industrial_score,
                scores.water_quality_score,
                scores.highest_severity,
                json.dumps(data)
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB Error] store_telemetry: {e}")

    def store_alert(self, alert: AlertEvent):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO alerts (
                    event_id, node_id, hazard_type, severity, score, timestamp,
                    timestamp_iso, title, reasons_json, sensor_evidence_json,
                    notification_tier, acknowledged, acknowledged_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.event_id,
                alert.node_id,
                alert.hazard_type,
                alert.severity,
                alert.score,
                alert.timestamp,
                alert.timestamp_iso,
                alert.title,
                json.dumps(alert.reasons),
                json.dumps(alert.sensor_evidence),
                alert.notification_tier,
                1 if alert.acknowledged else 0,
                alert.acknowledged_by
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB Error] store_alert: {e}")

    def get_recent_history(self, node_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        cached = self.recent_telemetry.get(node_id, [])
        if cached:
            return cached[-limit:]
        return []

    def get_trend_analysis(self, node_id: str, hours: int = 24) -> Dict[str, Any]:
        """
        Computes hourly aggregate trends for long-term cloud analysis.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cutoff = time.time() - (hours * 3600)
            cur.execute("""
                SELECT
                    AVG(temperature), MAX(temperature), MIN(temperature),
                    AVG(humidity), AVG(water_level_cm), MAX(water_level_cm),
                    AVG(soil_moisture_pct), MAX(vibration_hits),
                    AVG(flood_score), AVG(fire_score), AVG(pollution_score),
                    AVG(heat_score), AVG(landslide_score), AVG(industrial_score),
                    AVG(water_quality_score), COUNT(*)
                FROM telemetry
                WHERE node_id = ? AND timestamp >= ?
            """, (node_id, cutoff))
            row = cur.fetchone()
            conn.close()

            if row and row[15] and row[15] > 0:
                return {
                    "node_id": node_id,
                    "hours": hours,
                    "sample_count": row[15],
                    "temperature": {"avg": round(row[0] or 0, 1), "max": round(row[1] or 0, 1), "min": round(row[2] or 0, 1)},
                    "humidity_avg": round(row[3] or 0, 1),
                    "water_level": {"avg": round(row[4] or 0, 1), "max": round(row[5] or 0, 1)},
                    "soil_moisture_avg": round(row[6] or 0, 1),
                    "max_vibration_hits": row[7] or 0,
                    "avg_hazard_scores": {
                        "flood": round(row[8] or 0, 1),
                        "fire": round(row[9] or 0, 1),
                        "pollution": round(row[10] or 0, 1),
                        "heat": round(row[11] or 0, 1),
                        "landslide": round(row[12] or 0, 1),
                        "industrial": round(row[13] or 0, 1),
                        "water_quality": round(row[14] or 0, 1),
                    }
                }
        except Exception as e:
            print(f"[DB Error] get_trend_analysis: {e}")

        return {"node_id": node_id, "hours": hours, "sample_count": 0, "message": "No historical data in time window"}
