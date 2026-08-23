"""
SIH 2026 Environmental Monitoring Network
Storage Layer: SQLite Database and Fast In-Memory Cache
"""

import sqlite3
import json
import time
import os
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
        # In-memory fast cache: list of recent data per node
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
                flame_detected INTEGER,
                battery_voltage REAL,
                signal_strength INTEGER,
                flood_score REAL,
                fire_score REAL,
                pollution_score REAL,
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
                acknowledged INTEGER DEFAULT 0,
                acknowledged_by TEXT
            )
        """)

        # Indexes for fast historical range queries
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
                    water_rate_of_rise, flame_detected, battery_voltage, signal_strength,
                    flood_score, fire_score, pollution_score, highest_severity, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                1 if payload.flame_detected else 0,
                payload.battery_voltage,
                payload.signal_strength,
                scores.flood_score,
                scores.fire_score,
                scores.pollution_score,
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
                    acknowledged, acknowledged_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
