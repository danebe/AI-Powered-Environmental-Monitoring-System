"""
Environmental Intelligence Network
Data Models and Schema Definitions
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
import time


@dataclass
class Location:
    latitude: float = 28.6139
    longitude: float = 77.2090
    altitude_m: float = 216.0
    zone_description: str = "Field Station"


@dataclass
class SensorHealth:
    bme680:        str = "ONLINE"
    dht22:         str = "ONLINE"
    mq2:           str = "ONLINE"
    mq7:           str = "ONLINE"
    rain:          str = "ONLINE"
    ultrasonic:    str = "ONLINE"
    water_probe:   str = "ONLINE"
    flame:         str = "ONLINE"
    soil_moisture: str = "ONLINE"
    vibration:     str = "ONLINE"

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class TelemetryPayload:
    node_id:          str   = "NODE_001"
    timestamp:        float = field(default_factory=time.time)
    timestamp_iso:    str   = ""
    sequence_id:      int   = 0
    firmware_version: str   = "v2.0.0-ein"
    location: Location = field(default_factory=Location)

    # Atmospheric
    temperature:      float = 26.5
    humidity:         float = 62.0
    pressure:         float = 1012.8
    gas_resistance:   float = 120000.0   # BME680 Ohms — high = cleaner air

    # Gas & combustion (raw ADC)
    mq2_raw: int = 320
    mq7_raw: int = 280

    # Hydrological
    rain_raw:                   int   = 3850   # FC-37: lower = more rain
    water_level_raw:            int   = 120
    water_level_cm:             float = 12.5
    water_rate_of_rise_cm_min:  float = 0.0

    # Ground stability
    soil_moisture_raw: int   = 0
    soil_moisture_pct: float = 30.0    # FC-28: 0 % dry, 100 % saturated
    vibration_hits:    int   = 0       # SW-420: pulse count per 1 s window

    # Water quality (optional probes; default neutral if not wired)
    water_ph:           float = 7.0
    water_turbidity_ntu: float = 0.0

    # Optical & electrical
    flame_detected:  bool = False
    signal_strength: int  = -65        # Wi-Fi RSSI dBm

    sensor_health: SensorHealth = field(default_factory=SensorHealth)
    local_scores: Optional[Dict[str, float]] = None

    def __post_init__(self):
        if not self.timestamp_iso:
            self.timestamp_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.timestamp))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HazardScoreBreakdown:
    # --- Flood ---
    flood_score:    float = 0.0
    flood_severity: str   = "NORMAL"
    flood_reasons:  List[str] = field(default_factory=list)
    flood_weights:  Dict[str, float] = field(default_factory=dict)

    # --- Fire / Wildfire ---
    fire_score:    float = 0.0
    fire_severity: str   = "NORMAL"
    fire_reasons:  List[str] = field(default_factory=list)
    fire_weights:  Dict[str, float] = field(default_factory=dict)

    # --- Air Pollution ---
    pollution_score:    float = 0.0
    pollution_severity: str   = "NORMAL"
    pollution_reasons:  List[str] = field(default_factory=list)
    pollution_weights:  Dict[str, float] = field(default_factory=dict)

    # --- Extreme Heat ---
    heat_score:    float = 0.0
    heat_severity: str   = "NORMAL"
    heat_reasons:  List[str] = field(default_factory=list)
    heat_weights:  Dict[str, float] = field(default_factory=dict)

    # --- Landslide ---
    landslide_score:    float = 0.0
    landslide_severity: str   = "NORMAL"
    landslide_reasons:  List[str] = field(default_factory=list)
    landslide_weights:  Dict[str, float] = field(default_factory=dict)

    # --- Industrial Emissions ---
    industrial_score:    float = 0.0
    industrial_severity: str   = "NORMAL"
    industrial_reasons:  List[str] = field(default_factory=list)
    industrial_weights:  Dict[str, float] = field(default_factory=dict)

    # --- Water Quality ---
    water_quality_score:    float = 0.0
    water_quality_severity: str   = "NORMAL"
    water_quality_reasons:  List[str] = field(default_factory=list)
    water_quality_weights:  Dict[str, float] = field(default_factory=dict)

    # Overall
    highest_score:    float = 0.0
    highest_hazard:   str   = "NONE"
    highest_severity: str   = "NORMAL"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AlertEvent:
    event_id:   str
    node_id:    str
    hazard_type: str   # FLOOD | FIRE | POLLUTION | HEAT | LANDSLIDE | INDUSTRIAL | WATER_QUALITY
    severity:   str    # NORMAL | LOW | WARNING | CRITICAL
    score:      float
    timestamp:     float = field(default_factory=time.time)
    timestamp_iso: str   = ""
    title:   str = ""
    reasons: List[str]        = field(default_factory=list)
    sensor_evidence: Dict[str, Any] = field(default_factory=dict)
    acknowledged:    bool          = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[float] = None
    notification_tier: str = "CITIZEN"   # CITIZEN | AUTHORITY | EMERGENCY

    def __post_init__(self):
        if not self.timestamp_iso:
            self.timestamp_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.timestamp))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NodeMetadata:
    node_id:   str
    name:      str
    location:  Location
    zone_type: str   = "URBAN"   # INDUSTRIAL | FOREST | RIVER | AGRICULTURAL
    status:    str   = "ONLINE"  # ONLINE | DEGRADED | OFFLINE
    last_seen: float = field(default_factory=time.time)
    firmware_version: str = "v2.0.0-ein"
    signal_strength:  int = -65
    active_alerts_count: int = 0
    latest_scores: Optional[HazardScoreBreakdown] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SystemThresholds:
    # Severity bands
    normal_max:   float = 24.0
    low_max:      float = 49.0
    warning_max:  float = 74.0
    critical_min: float = 75.0

    # Flood
    water_level_warning_cm:          float = 35.0
    water_level_critical_cm:         float = 65.0
    water_rise_rate_warning_cm_min:  float = 2.5
    water_rise_rate_critical_cm_min: float = 6.0

    # Fire / combustion
    temp_warning_c:                float = 42.0
    temp_critical_c:               float = 52.0
    temp_rise_rate_critical_c_min: float = 4.0
    mq2_smoke_warning_pct:         float = 45.0
    mq2_smoke_critical_pct:        float = 75.0

    # Pollution
    bme680_gas_res_warning_ohms:  float = 60000.0
    bme680_gas_res_critical_ohms: float = 20000.0
    mq7_co_warning_pct:           float = 45.0
    mq7_co_critical_pct:          float = 75.0

    # Extreme heat
    temp_heat_warning_c:  float = 42.0
    temp_heat_critical_c: float = 50.0

    # Landslide
    soil_moisture_warning_pct:  float = 65.0
    soil_moisture_critical_pct: float = 85.0
    vibration_warning_hits:     int   = 10
    vibration_critical_hits:    int   = 30

    # Water quality
    water_ph_warning_deviation:    float = 1.5   # from neutral 7.0
    water_ph_critical_deviation:   float = 2.5
    water_turbidity_warning_ntu:   float = 50.0
    water_turbidity_critical_ntu:  float = 200.0

    # Alert cooldown & persistence
    alert_cooldown_seconds:       float = 45.0
    consecutive_spikes_required:  int   = 3

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
