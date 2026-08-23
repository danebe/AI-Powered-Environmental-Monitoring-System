"""
SIH 2026 Environmental Monitoring Network
Data Models and Schema Definitions
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
import time
import json


@dataclass
class Location:
    latitude: float = 28.6139
    longitude: float = 77.2090
    altitude_m: float = 216.0
    zone_description: str = "Forest Edge Station"


@dataclass
class SensorHealth:
    bme680: str = "ONLINE"       # ONLINE | DEGRADED | OFFLINE | INVALID | CALIBRATING
    dht22: str = "ONLINE"
    mq2: str = "ONLINE"
    mq7: str = "ONLINE"
    rain: str = "ONLINE"
    ultrasonic: str = "ONLINE"
    water_probe: str = "ONLINE"
    flame: str = "ONLINE"

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class TelemetryPayload:
    node_id: str = "NODE_001"
    timestamp: float = field(default_factory=time.time)
    timestamp_iso: str = ""
    sequence_id: int = 0
    firmware_version: str = "v1.4.0-sih2026"
    location: Location = field(default_factory=Location)

    # Atmospheric
    temperature: float = 26.5
    humidity: float = 62.0
    pressure: float = 1012.8
    gas_resistance: float = 120000.0  # BME680 Ohms

    # Gas & Combustion Raw ADC
    mq2_raw: int = 320
    mq7_raw: int = 280

    # Hydrological
    rain_raw: int = 3850              # Lower = more rain (0-4095)
    water_level_raw: int = 120        # Conductive probe ADC
    water_level_cm: float = 12.5      # Ultrasonic derived depth
    water_rate_of_rise_cm_min: float = 0.0

    # Optical & Electrical
    flame_detected: bool = False
    battery_voltage: float = 3.85
    signal_strength: int = -65        # RSSI in dBm

    sensor_health: SensorHealth = field(default_factory=SensorHealth)
    local_scores: Optional[Dict[str, float]] = None

    def __post_init__(self):
        if not self.timestamp_iso:
            self.timestamp_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.timestamp))

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


@dataclass
class HazardScoreBreakdown:
    flood_score: float = 0.0
    flood_severity: str = "NORMAL"     # NORMAL | LOW | WARNING | CRITICAL
    flood_reasons: List[str] = field(default_factory=list)
    flood_weights: Dict[str, float] = field(default_factory=dict)

    fire_score: float = 0.0
    fire_severity: str = "NORMAL"
    fire_reasons: List[str] = field(default_factory=list)
    fire_weights: Dict[str, float] = field(default_factory=dict)

    pollution_score: float = 0.0
    pollution_severity: str = "NORMAL"
    pollution_reasons: List[str] = field(default_factory=list)
    pollution_weights: Dict[str, float] = field(default_factory=dict)

    highest_score: float = 0.0
    highest_hazard: str = "NONE"
    highest_severity: str = "NORMAL"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AlertEvent:
    event_id: str
    node_id: str
    hazard_type: str                  # FLOOD | FIRE | POLLUTION
    severity: str                     # NORMAL | LOW | WARNING | CRITICAL
    score: float
    timestamp: float = field(default_factory=time.time)
    timestamp_iso: str = ""
    title: str = ""
    reasons: List[str] = field(default_factory=list)
    sensor_evidence: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[float] = None

    def __post_init__(self):
        if not self.timestamp_iso:
            self.timestamp_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.timestamp))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NodeMetadata:
    node_id: str
    name: str
    location: Location
    status: str = "ONLINE"             # ONLINE | DEGRADED | OFFLINE
    last_seen: float = field(default_factory=time.time)
    firmware_version: str = "v1.4.0-sih2026"
    battery_voltage: float = 3.85
    signal_strength: int = -65
    active_alerts_count: int = 0
    latest_scores: Optional[HazardScoreBreakdown] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SystemThresholds:
    normal_max: float = 24.0
    low_max: float = 49.0
    warning_max: float = 74.0
    critical_min: float = 75.0

    # Hydrological
    water_level_warning_cm: float = 35.0
    water_level_critical_cm: float = 65.0
    water_rise_rate_warning_cm_min: float = 2.5
    water_rise_rate_critical_cm_min: float = 6.0

    # Fire
    temp_warning_c: float = 42.0
    temp_critical_c: float = 52.0
    temp_rise_rate_critical_c_min: float = 4.0
    mq2_smoke_warning_pct: float = 45.0
    mq2_smoke_critical_pct: float = 75.0

    # Pollution
    bme680_gas_res_warning_ohms: float = 60000.0
    bme680_gas_res_critical_ohms: float = 20000.0
    mq7_co_warning_pct: float = 45.0
    mq7_co_critical_pct: float = 75.0

    # Cooldown & Persistence
    alert_cooldown_seconds: float = 45.0
    consecutive_spikes_required: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
