/**
 * Environmental Intelligence Network — Interactive Geospatial Risk Map
 * Uses Leaflet.js with clean vector styling & dynamic risk halo rings
 */

class RiskMap {
  constructor(containerId = "leaflet-map", center = [13.0850, 80.2101], zoom = 11) {
    this.containerId = containerId;
    this.center = center;
    this.zoom = zoom;
    this.map = null;
    this.markers = {};
    this.riskCircles = {};
    this.initialized = false;
    this.currentTheme = "light";
    this.tileLayer = null;

    this.zoneIcons = {
      INDUSTRIAL: "🏭",
      FOREST: "🌲",
      RIVER: "🌊",
      AGRICULTURAL: "⛰️",
      URBAN: "🏙️"
    };

    this.zoneColors = {
      INDUSTRIAL: "#64748b",
      FOREST: "#16a34a",
      RIVER: "#0284c7",
      AGRICULTURAL: "#d97706",
      URBAN: "#7c3aed"
    };

    this.initMap();
  }

  initMap() {
    const el = document.getElementById(this.containerId);
    if (!el || typeof L === "undefined") {
      return;
    }

    try {
      this.map = L.map(this.containerId, {
        center: this.center,
        zoom: this.zoom,
        zoomControl: true,
        attributionControl: false
      });

      this.updateTileLayer("light");

      // Custom Attribution
      L.control.attribution({ position: "bottomright", prefix: false })
        .addAttribution("&copy; OpenStreetMap | Environmental Intelligence")
        .addTo(this.map);

      this.initialized = true;
    } catch (e) {
      console.warn("[RiskMap] Init failed:", e);
    }
  }

  updateTileLayer(theme = "light") {
    if (!this.map) return;
    this.currentTheme = theme;

    if (this.tileLayer) {
      this.map.removeLayer(this.tileLayer);
    }

    let tileUrl = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
    if (theme === "dark" || theme === "black") {
      tileUrl = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
    }

    this.tileLayer = L.tileLayer(tileUrl, {
      maxZoom: 19,
      subdomains: "abcd"
    }).addTo(this.map);
  }

  getRiskColor(score, severity) {
    if (severity === "CRITICAL" || score >= 75.0) return "#dc2626"; // Red
    if (severity === "WARNING" || score >= 50.0) return "#ea580c";  // Orange
    if (severity === "LOW" || score >= 25.0) return "#ca8a04";      // Yellow
    return "#16a34a"; // Green
  }

  createNodeIcon(nodeId, zoneType, score, severity, isOnline) {
    const emoji = this.zoneIcons[zoneType] || "📡";
    const color = this.getRiskColor(score, severity);
    const borderColor = isOnline ? color : "#94a3b8";

    const html = `
      <div class="custom-node-marker ${isOnline ? 'online' : 'offline'}" style="border-color:${borderColor};">
        <span class="marker-emoji">${emoji}</span>
        <span class="marker-score" style="background:${color};">${Math.round(score)}</span>
      </div>
    `;

    return L.divIcon({
      html: html,
      className: "node-leaflet-div-icon",
      iconSize: [36, 36],
      iconAnchor: [18, 18],
      popupAnchor: [0, -20]
    });
  }

  updateNodes(nodes = [], latestStates = {}, onSelectNodeCallback = null) {
    if (!this.initialized || !this.map) return;

    nodes.forEach(node => {
      const nid = node.node_id;
      const state = latestStates[nid] || {};
      const scores = state.scores || {};
      const highestScore = scores.highest_score || 0.0;
      const highestSev = scores.highest_severity || "NORMAL";
      const highestHazard = scores.highest_hazard || "NONE";
      const isOnline = node.status === "ONLINE";

      const loc = node.location || {};
      const lat = loc.latitude || 13.0850;
      const lon = loc.longitude || 80.2101;
      const zone = node.zone_type || "URBAN";

      const icon = this.createNodeIcon(nid, zone, highestScore, highestSev, isOnline);
      const riskColor = this.getRiskColor(highestScore, highestSev);

      // 1. Update or Create Marker
      if (this.markers[nid]) {
        this.markers[nid].setLatLng([lat, lon]);
        this.markers[nid].setIcon(icon);
      } else {
        const marker = L.marker([lat, lon], { icon: icon }).addTo(this.map);
        marker.on("click", () => {
          if (typeof onSelectNodeCallback === "function") {
            onSelectNodeCallback(nid);
          }
        });
        this.markers[nid] = marker;
      }

      // Popup Content
      const popupHtml = `
        <div class="map-popup-card">
          <div class="map-popup-header">
            <strong>${node.name || nid}</strong>
            <span class="map-popup-status ${isOnline ? 'online' : 'offline'}">${node.status}</span>
          </div>
          <div class="map-popup-body">
            <div><strong>Zone:</strong> ${zone}</div>
            <div><strong>Peak Hazard:</strong> ${highestHazard} (${highestScore}/100)</div>
            <div><strong>Status:</strong> ${highestSev}</div>
          </div>
        </div>
      `;
      this.markers[nid].bindPopup(popupHtml);

      // 2. Update Risk Radius Circle (Heat Halo)
      const radius = isOnline ? Math.max(80, highestScore * 4.0) : 40;
      const fillOpacity = isOnline ? Math.min(0.35, 0.08 + (highestScore / 100) * 0.25) : 0.04;

      if (this.riskCircles[nid]) {
        this.riskCircles[nid].setLatLng([lat, lon]);
        this.riskCircles[nid].setRadius(radius);
        this.riskCircles[nid].setStyle({
          color: riskColor,
          fillColor: riskColor,
          fillOpacity: fillOpacity
        });
      } else {
        const circle = L.circle([lat, lon], {
          radius: radius,
          color: riskColor,
          fillColor: riskColor,
          fillOpacity: fillOpacity,
          weight: 1.5
        }).addTo(this.map);
        this.riskCircles[nid] = circle;
      }
    });
  }

  focusNode(lat, lon) {
    if (this.map && lat && lon) {
      this.map.panTo([lat, lon], { animate: true, duration: 0.8 });
    }
  }

  invalidateSize() {
    if (this.map) {
      setTimeout(() => this.map.invalidateSize(), 200);
    }
  }
}
