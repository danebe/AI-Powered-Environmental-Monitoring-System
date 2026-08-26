/**
 * Environmental Intelligence Network — Dashboard Application Controller
 * Manages real-time SSE stream, 7-hazard scoring, Leaflet map, notifications,
 * Web Serial / USB hardware link, and 15 physical simulation scenarios.
 */

class DashboardApp {
  constructor() {
    this.authenticated = true; // Auto-auth in demo mode, modal available
    this.activeNodeId = "NODE_001";
    this.selectedNotificationTier = "ALL";
    this.alarmActive = true;
    this.audioSilenced = false;
    this.currentTheme = "light";

    // Audio players
    this.audioWarning = new Audio("sounds/eas_warning.wav");
    this.audioFlood = new Audio("sounds/eas_flood.wav");
    this.audioFire = new Audio("sounds/eas_fire.wav");
    this.audioGas = new Audio("sounds/eas_gas.wav");

    // Time-series ring buffers for SVG charts — 60-second window at 1 Hz
    this.chartData = {
      timestamps: [],
      water_level: [],
      rain_intensity: [],
      mq2_smoke: [],
      temperature: [],
      flood_score: [],
      fire_score: [],
      industrial_score: []
    };

    // Hazard score tracking for trend arrows (previous sample)
    this.prevHazardScores = {};

    // Desktop notification cooldown map: alertId -> last fired timestamp
    this.notificationCooldowns = {};
    this.desktopNotifEnabled = false;
    this._requestNotificationPermission();

    // Geospatial Leaflet Map instance
    this.riskMap = new RiskMap("leaflet-map");

    // Web Serial API port reference
    this.webSerialPort = null;
    this.webSerialReader = null;
    this.webSerialRunning = false;

    this.init();
  }

  init() {
    this.bindThemeToggle();
    this.bindAlarmControls();
    this.bindAuthModal();
    this.bindScenarioButtons();
    this.bindNotificationTabs();
    this.bindHardwareControls();

    // Start Real-Time SSE Stream with auto-fallback to REST polling
    this.startDataStream();

    // Start system clock
    setInterval(() => this.updateClock(), 1000);
    this.updateClock();

    // Periodic hardware & notification status polling
    setInterval(() => this.pollHardwareStatus(), 4000);
    this.pollHardwareStatus();

    // In-app toast container
    this._ensureToastContainer();
  }

  // --------------------------------------------------------------------------
  // THEME SWITCHER (Light / Dark / OLED Black)
  // --------------------------------------------------------------------------
  bindThemeToggle() {
    const btns = [
      { id: "btn-theme-light", theme: "light" },
      { id: "btn-theme-dark", theme: "dark" },
      { id: "btn-theme-black", theme: "black" }
    ];

    btns.forEach(b => {
      const el = document.getElementById(b.id);
      if (el) {
        el.addEventListener("click", () => {
          this.setTheme(b.theme);
        });
      }
    });
  }

  setTheme(theme) {
    this.currentTheme = theme;
    document.body.className = `theme-${theme}`;

    ["btn-theme-light", "btn-theme-dark", "btn-theme-black"].forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.classList.toggle("active", el.dataset.theme === theme);
      }
    });

    // Update map tile layer styling
    if (this.riskMap) {
      this.riskMap.updateTileLayer(theme);
    }
  }

  // --------------------------------------------------------------------------
  // MASTER ALARM CONTROLS
  // --------------------------------------------------------------------------
  bindAlarmControls() {
    const toggleBtn = document.getElementById("btn-alarm-toggle");
    const silenceBtn = document.getElementById("btn-silence-alarm");

    if (toggleBtn) {
      toggleBtn.addEventListener("click", () => {
        this.alarmActive = !this.alarmActive;
        toggleBtn.classList.toggle("active", this.alarmActive);
        document.getElementById("alarm-icon").textContent = this.alarmActive ? "🚨" : "🔕";
        document.getElementById("alarm-text").textContent = this.alarmActive ? "ALARM: ON" : "ALARM: MUTED";
        if (!this.alarmActive) {
          this.stopAllSounds();
        }
      });
    }

    if (silenceBtn) {
      silenceBtn.addEventListener("click", () => {
        this.audioSilenced = true;
        this.stopAllSounds();
        const banner = document.getElementById("emergency-banner");
        if (banner) banner.classList.add("hidden");
      });
    }
  }

  stopAllSounds() {
    [this.audioWarning, this.audioFlood, this.audioFire, this.audioGas].forEach(a => {
      try {
        a.pause();
        a.currentTime = 0;
      } catch (e) {}
    });
  }

  playHazardSound(hazardType, severity) {
    if (!this.alarmActive || this.audioSilenced) return;

    try {
      if (severity === "CRITICAL" || severity === "WARNING") {
        let audioToPlay = this.audioWarning;
        if (hazardType === "FLOOD" || hazardType === "LANDSLIDE") {
          audioToPlay = this.audioFlood;
        } else if (hazardType === "FIRE" || hazardType === "HEAT") {
          audioToPlay = this.audioFire;
        } else if (hazardType === "POLLUTION" || hazardType === "INDUSTRIAL") {
          audioToPlay = this.audioGas;
        }

        // Only start playback if not already actively playing (prevents 1Hz choppy stuttering)
        if (audioToPlay && (audioToPlay.paused || audioToPlay.ended)) {
          audioToPlay.play().catch(() => {});
        }
      }
    } catch (e) {
      // Browser autoplay policy catch
    }
  }

  // --------------------------------------------------------------------------
  // AUTHENTICATION MODAL
  // --------------------------------------------------------------------------
  bindAuthModal() {
    const modal = document.getElementById("login-modal");
    const form = document.getElementById("login-form");
    const errorEl = document.getElementById("login-error");
    const logoutBtn = document.getElementById("btn-logout");

    // Hide login modal by default for instant evaluation
    if (modal) modal.classList.add("hidden");

    if (form) {
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        const u = document.getElementById("input-username").value.trim();
        const p = document.getElementById("input-password").value.trim();

        if ((u === "admin" && p === "admin123") || (u === "operator" && p === "operator123")) {
          this.authenticated = true;
          modal.classList.add("hidden");
          document.getElementById("stat-user-name").textContent = u.charAt(0).toUpperCase() + u.slice(1);
          if (errorEl) errorEl.classList.add("hidden");
        } else {
          if (errorEl) errorEl.classList.remove("hidden");
        }
      });
    }

    if (logoutBtn) {
      logoutBtn.addEventListener("click", () => {
        this.authenticated = false;
        if (modal) modal.classList.remove("hidden");
      });
    }
  }

  // --------------------------------------------------------------------------
  // SCENARIO INJECTOR BINDINGS (15 Scenarios)
  // --------------------------------------------------------------------------
  bindScenarioButtons() {
    const buttons = document.querySelectorAll(".scenario-btn");
    buttons.forEach(btn => {
      btn.addEventListener("click", () => {
        const sc = btn.dataset.scenario;
        this.injectScenario(sc);
      });
    });

    const resetBtn = document.getElementById("btn-reset-normal");
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        this.injectScenario("NORMAL");
      });
    }
  }

  injectScenario(scenario) {
    fetch("/api/simulator/scenario", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: jsonStringifySafe({ scenario: scenario, node_id: this.activeNodeId })
    })
      .then(r => r.json())
      .then(res => {
        this.audioSilenced = false; // Reset audio silence on new scenario
        this.updateActiveScenarioButtons(scenario);
      })
      .catch(err => console.warn("[Scenario] Inject error:", err));
  }

  updateActiveScenarioButtons(activeScenario) {
    document.querySelectorAll(".scenario-btn").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.scenario === activeScenario);
    });
  }

  // --------------------------------------------------------------------------
  // NOTIFICATION TABS
  // --------------------------------------------------------------------------
  bindNotificationTabs() {
    const tabs = document.querySelectorAll(".notif-tab-btn");
    tabs.forEach(tab => {
      tab.addEventListener("click", () => {
        tabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        this.selectedNotificationTier = tab.dataset.tier;
        this.fetchAndRenderNotifications();
      });
    });
  }

  // --------------------------------------------------------------------------
  // REAL HARDWARE CONTROLS (USB / Web Serial / Manual)
  // --------------------------------------------------------------------------
  bindHardwareControls() {
    const connectBtn = document.getElementById("btn-hw-connect");
    const disconnectBtn = document.getElementById("btn-hw-disconnect");
    const webSerialBtn = document.getElementById("btn-web-serial");
    const manualIngestBtn = document.getElementById("btn-hw-manual-ingest");

    // Server-Side Serial Reader Connect (e.g. COM3)
    if (connectBtn) {
      connectBtn.addEventListener("click", () => {
        const port = document.getElementById("hw-port-input").value.trim() || "COM3";
        fetch("/api/hardware/connect", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: jsonStringifySafe({ port: port, baud: 115200 })
        })
          .then(r => r.json())
          .then(() => this.pollHardwareStatus())
          .catch(e => console.warn("[Hardware] Connect error:", e));
      });
    }

    if (disconnectBtn) {
      disconnectBtn.addEventListener("click", () => {
        fetch("/api/hardware/disconnect", { method: "POST" })
          .then(() => this.pollHardwareStatus())
          .catch(e => console.warn("[Hardware] Disconnect error:", e));
      });
    }

    // Browser Web Serial API (Chrome/Edge direct USB reading)
    if (webSerialBtn) {
      if (!("serial" in navigator)) {
        webSerialBtn.textContent = "⚡ Web Serial (Use Chrome/Edge)";
        webSerialBtn.disabled = true;
        webSerialBtn.style.opacity = "0.5";
      } else {
        webSerialBtn.addEventListener("click", () => this.toggleWebSerial());
      }
    }

    // Manual JSON Textarea Ingest
    if (manualIngestBtn) {
      manualIngestBtn.addEventListener("click", () => {
        const txt = document.getElementById("hw-manual-json").value.trim();
        if (!txt) return;
        try {
          const payload = JSON.parse(txt);
          fetch("/api/hardware/ingest", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: jsonStringifySafe(payload)
          })
            .then(r => r.json())
            .then(res => {
              alert("Telemetry successfully ingested into node: " + (payload.node_id || "NODE_001"));
            })
            .catch(err => alert("Ingestion failed: " + err));
        } catch (e) {
          alert("Invalid JSON format: " + e.message);
        }
      });
    }
  }

  async toggleWebSerial() {
    if (this.webSerialRunning) {
      this.webSerialRunning = false;
      if (this.webSerialReader) await this.webSerialReader.cancel();
      if (this.webSerialPort) await this.webSerialPort.close();
      document.getElementById("btn-web-serial").textContent = "⚡ Web Serial API (Chrome/Edge)";
      document.getElementById("hw-status-badge").textContent = "STANDBY";
      return;
    }

    try {
      this.webSerialPort = await navigator.serial.requestPort();
      await this.webSerialPort.open({ baudRate: 115200 });
      this.webSerialRunning = true;
      document.getElementById("btn-web-serial").textContent = "🔌 Stop Web Serial Stream";
      document.getElementById("hw-status-badge").textContent = "WEB SERIAL LIVE";

      const textDecoder = new TextDecoderStream();
      const readableStreamClosed = this.webSerialPort.readable.pipeTo(textDecoder.writable);
      this.webSerialReader = textDecoder.readable.getReader();

      let lineBuffer = "";
      while (this.webSerialRunning) {
        const { value, done } = await this.webSerialReader.read();
        if (done) break;
        lineBuffer += value;
        const lines = lineBuffer.split("\n");
        lineBuffer = lines.pop(); // Keep partial line

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
            try {
              const parsed = JSON.parse(trimmed);
              fetch("/api/hardware/ingest", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: jsonStringifySafe(parsed)
              });
            } catch (e) {}
          }
        }
      }
    } catch (err) {
      console.warn("[WebSerial] Error:", err);
      alert("Web Serial error: " + err.message);
      this.webSerialRunning = false;
    }
  }

  pollHardwareStatus() {
    fetch("/api/hardware/status")
      .then(r => r.json())
      .then(status => {
        const label = document.getElementById("hw-port-label");
        const count = document.getElementById("hw-packets-count");
        const badge = document.getElementById("hw-status-badge");
        const connBtn = document.getElementById("btn-hw-connect");
        const discBtn = document.getElementById("btn-hw-disconnect");

        if (status.connected) {
          if (label) label.textContent = `${status.port} (${status.baud} baud)`;
          if (count) count.textContent = `${status.packets_ingested} pkts`;
          if (badge) badge.textContent = "CONNECTED";
          if (connBtn) connBtn.classList.add("hidden");
          if (discBtn) discBtn.classList.remove("hidden");
        } else {
          if (label) label.textContent = "Disconnected";
          if (count) count.textContent = `${status.packets_ingested} pkts`;
          if (badge && !this.webSerialRunning) badge.textContent = "STANDBY";
          if (connBtn) connBtn.classList.remove("hidden");
          if (discBtn) discBtn.classList.add("hidden");
        }
      })
      .catch(() => {});
  }

  // --------------------------------------------------------------------------
  // REAL-TIME DATA STREAM (SSE with REST Polling Fallback)
  // --------------------------------------------------------------------------
  startDataStream() {
    if (!!window.EventSource) {
      const source = new EventSource("/api/stream");

      source.onmessage = (event) => {
        try {
          const overview = JSON.parse(event.data);
          this.renderOverview(overview);
        } catch (e) {
          console.warn("[SSE] Parse error:", e);
        }
      };

      source.onerror = () => {
        // Fallback to periodic REST polling if SSE is disconnected
        setTimeout(() => this.fetchRestOverview(), 1500);
      };
    } else {
      setInterval(() => this.fetchRestOverview(), 1000);
    }
  }

  fetchRestOverview() {
    fetch("/api/overview")
      .then(r => r.json())
      .then(overview => this.renderOverview(overview))
      .catch(() => {});
  }

  // --------------------------------------------------------------------------
  // MAIN RENDER PIPELINE
  // --------------------------------------------------------------------------
  renderOverview(overview) {
    if (!overview) return;

    // 1. Header Metrics
    document.getElementById("stat-online-nodes").textContent = overview.online_nodes;
    document.getElementById("stat-total-nodes").textContent = overview.total_nodes;
    document.getElementById("stat-active-alerts").textContent = overview.active_alerts_count;

    const maxHazEl = document.getElementById("stat-max-hazard");
    const peakScore = Math.round(overview.highest_hazard_score);
    maxHazEl.textContent = `${overview.highest_hazard_type} (${peakScore})`;

    // Metric pill color class
    const hazardPill = document.getElementById("pill-hazard");
    hazardPill.className = `metric-pill ${peakScore >= 75 ? 'danger' : (peakScore >= 50 ? 'warning' : 'healthy')}`;

    // 2. Active Emergency Banner + Desktop/Toast Notifications
    const banner = document.getElementById("emergency-banner");
    const criticalAlerts = (overview.active_alerts || []).filter(a => a.severity === "CRITICAL");
    if (criticalAlerts.length > 0 && !this.audioSilenced) {
      banner.classList.remove("hidden");
      const topAlert = criticalAlerts[0];
      document.getElementById("emergency-title").textContent = topAlert.title || "CRITICAL HAZARD DETECTED";
      document.getElementById("emergency-desc").textContent = (topAlert.reasons || [])[0] || "Immediate danger detected.";
      document.getElementById("emergency-action").textContent = `ACTION: EVACUATE ${topAlert.node_id}`;
      this.playHazardSound(topAlert.hazard_type, topAlert.severity);
      // Fire desktop + in-app toast notification (with 60s cooldown)
      criticalAlerts.forEach(a => this._fireDesktopNotification(a));
    } else if (criticalAlerts.length === 0) {
      banner.classList.add("hidden");
    }

    // 3. Render Node List
    this.renderNodeList(overview.nodes || [], overview.latest_states || {});

    // 4. Render Active Node State
    const activeState = (overview.latest_states || {})[this.activeNodeId];
    if (activeState) {
      this.renderTelemetryGrid(activeState);
      this.renderHazardScores(activeState.scores || {});
      this.renderOledMirror(activeState);
      this.pushChartSample(activeState);
    }

    // 5. Update Leaflet Map
    if (this.riskMap) {
      this.riskMap.updateNodes(overview.nodes || [], overview.latest_states || {}, (nodeId) => {
        this.selectNode(nodeId);
      });
    }

    // 6. Update Notification Feed
    this.renderNotificationFeed(overview.active_alerts || []);

    // 7. Update Scenario Active Button State
    this.updateActiveScenarioButtons(overview.active_scenario);
  }

  // --------------------------------------------------------------------------
  // NODE LIST RENDERING
  // --------------------------------------------------------------------------
  renderNodeList(nodes, latestStates) {
    const container = document.getElementById("node-list-container");
    if (!container) return;

    let html = "";
    nodes.forEach(node => {
      const nid = node.node_id;
      const state = latestStates[nid] || {};
      const scores = state.scores || {};
      const highestScore = Math.round(scores.highest_score || 0);
      const isSelected = nid === this.activeNodeId;
      const zone = node.zone_type || "URBAN";

      html += `
        <div class="node-item-card ${isSelected ? 'active' : ''}" onclick="window.app.selectNode('${nid}')">
          <div class="node-item-header">
            <span class="node-item-name">${node.name || nid}</span>
            <span class="zone-tag ${zone}">${zone}</span>
          </div>
          <div class="node-item-meta">
            <span>Status: <strong style="color:${node.status === 'ONLINE' ? '#16a34a' : '#dc2626'}">${node.status}</strong></span>
            <span>Peak Risk: <strong>${highestScore}/100</strong></span>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  }

  selectNode(nodeId) {
    this.activeNodeId = nodeId;
    document.getElementById("active-node-name").textContent = nodeId;

    // Reset chart buffers on node change
    this.chartData = {
      timestamps: [],
      water_level: [],
      rain_intensity: [],
      mq2_smoke: [],
      temperature: [],
      flood_score: [],
      fire_score: [],
      industrial_score: []
    };
    this.prevHazardScores = {};

    fetch("/api/overview")
      .then(r => r.json())
      .then(overview => this.renderOverview(overview));
  }

  // --------------------------------------------------------------------------
  // TELEMETRY READOUT GRID
  // --------------------------------------------------------------------------
  renderTelemetryGrid(state) {
    const norm = state.normalized || {};
    const read = state.readings || {};

    const setVal = (id, val, colorClass) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent = val;
      if (colorClass) {
        el.className = el.className.replace(/\bval-(safe|warn|danger)\b/g, "");
        el.classList.add(`val-${colorClass}`);
      }
    };

    // Temperature: safe <35, warn 35-45, danger >45
    const temp = norm.temperature_c;
    setVal("tel-temp-val", temp !== undefined ? temp.toFixed(1) : "--",
      temp === undefined ? null : temp > 45 ? "danger" : temp > 35 ? "warn" : "safe");

    // Humidity
    const hum = norm.humidity_pct;
    setVal("tel-hum-val", hum !== undefined ? Math.round(hum) : "--",
      hum === undefined ? null : hum > 90 ? "danger" : hum > 75 ? "warn" : "safe");

    setVal("tel-pres-val", norm.pressure_hpa !== undefined ? Math.round(norm.pressure_hpa) : "--");

    // Gas resistance: danger <20k, warn <50k, safe >50k (high = clean air)
    const gasRes = norm.gas_resistance_ohms;
    setVal("tel-gasres-val", gasRes !== undefined ? (gasRes / 1000).toFixed(1) : "--",
      gasRes === undefined ? null : gasRes < 20000 ? "danger" : gasRes < 50000 ? "warn" : "safe");

    // MQ-2: ADC safe <500, warn 500-1500, danger >1500
    const mq2 = read.mq2_raw;
    setVal("tel-mq2-val", mq2 || "--",
      mq2 === undefined ? null : mq2 > 1500 ? "danger" : mq2 > 500 ? "warn" : "safe");
    setVal("tel-mq2-pct", `Anomaly: ${Math.round(norm.mq2_anomaly_pct || 0)}%`);

    const mq7 = read.mq7_raw;
    setVal("tel-mq7-val", mq7 || "--",
      mq7 === undefined ? null : mq7 > 1200 ? "danger" : mq7 > 450 ? "warn" : "safe");
    setVal("tel-mq7-pct", `Anomaly: ${Math.round(norm.mq7_anomaly_pct || 0)}%`);

    // Rain: warn >40%, danger >75%
    const rain = Math.round(norm.rain_intensity_pct || 0);
    setVal("tel-rain-val", rain, rain > 75 ? "danger" : rain > 40 ? "warn" : "safe");

    // Water level: warn >40cm, danger >70cm
    const water = norm.water_level_cm;
    setVal("tel-water-val", water !== undefined ? water.toFixed(1) : "--",
      water === undefined ? null : water > 70 ? "danger" : water > 40 ? "warn" : "safe");

    const rateStr = `${norm.water_rate_of_rise_cm_min >= 0 ? '+' : ''}${(norm.water_rate_of_rise_cm_min || 0).toFixed(1)} cm/m`;
    const rateEl = document.getElementById("tel-waterrate-val");
    if (rateEl) {
      rateEl.textContent = rateStr;
      const rate = norm.water_rate_of_rise_cm_min || 0;
      rateEl.style.color = rate > 5 ? "#dc2626" : rate > 2 ? "#ea580c" : "inherit";
    }

    // Soil: warn >65%, danger >85%
    const soil = norm.soil_moisture_pct || 0;
    setVal("tel-soil-val", soil.toFixed(1), soil > 85 ? "danger" : soil > 65 ? "warn" : "safe");

    // Vibration: warn >5, danger >20
    const vib = norm.vibration_hits || 0;
    setVal("tel-vib-val", vib, vib > 20 ? "danger" : vib > 5 ? "warn" : "safe");

    setVal("tel-rssi-val", `${read.signal_strength || -65} dBm`);

    const flameEl = document.getElementById("tel-flame-val");
    if (flameEl) {
      if (norm.flame_detected) {
        flameEl.textContent = "🔥 ACTIVE BLAZE";
        flameEl.style.color = "#dc2626";
      } else {
        flameEl.textContent = "CLEAR";
        flameEl.style.color = "var(--sev-normal-text)";
      }
    }
  }

  // --------------------------------------------------------------------------
  // 6 CORE HAZARD SCORES RENDERING (with trend arrows)
  // --------------------------------------------------------------------------
  renderHazardScores(scores) {
    const hazards = [
      { key: "flood",      prefix: "flood" },
      { key: "fire",       prefix: "fire" },
      { key: "pollution",  prefix: "pollution" },
      { key: "heat",       prefix: "heat" },
      { key: "landslide",  prefix: "landslide" },
      { key: "industrial", prefix: "industrial" }
    ];

    hazards.forEach(h => {
      const score    = Math.round(scores[`${h.key}_score`] || 0);
      const sev      = scores[`${h.key}_severity`] || "NORMAL";
      const reasons  = scores[`${h.key}_reasons`] || [];
      const prevScore = this.prevHazardScores[h.key] || 0;
      const delta    = score - prevScore;

      const scoreEl   = document.getElementById(`score-${h.prefix}-val`);
      const badgeEl   = document.getElementById(`badge-${h.prefix}`);
      const fillEl    = document.getElementById(`fill-${h.prefix}`);
      const factorsEl = document.getElementById(`factors-${h.prefix}`);
      const arrowEl   = document.getElementById(`arrow-${h.prefix}`);
      const cardEl    = document.getElementById(`card-${h.prefix === 'water-quality' ? 'water-quality' : h.prefix}`);

      if (scoreEl) scoreEl.textContent = score;

      // Trend arrow
      if (arrowEl) {
        if (delta > 2)       { arrowEl.textContent = "↑"; arrowEl.className = "trend-arrow up"; }
        else if (delta < -2) { arrowEl.textContent = "↓"; arrowEl.className = "trend-arrow down"; }
        else                 { arrowEl.textContent = "→"; arrowEl.className = "trend-arrow flat"; }
      }

      if (badgeEl) {
        badgeEl.textContent = `[${sev}]`;
        badgeEl.className = `severity-badge sev-${sev}`;
      }

      if (fillEl) {
        fillEl.style.width = `${Math.min(100, Math.max(0, score))}%`;
        fillEl.style.backgroundColor = score >= 75 ? "#dc2626" : (score >= 50 ? "#ea580c" : (score >= 25 ? "#ca8a04" : "#16a34a"));
      }

      if (factorsEl) {
        factorsEl.textContent = reasons.length > 0 ? `• ${reasons[0]}` : "• Baseline nominal";
      }

      // Card pulse class
      if (cardEl) {
        cardEl.classList.remove("card-warning", "card-critical");
        if (sev === "CRITICAL") cardEl.classList.add("card-critical");
        else if (sev === "WARNING") cardEl.classList.add("card-warning");
      }

      this.prevHazardScores[h.key] = score;
    });
  }

  // --------------------------------------------------------------------------
  // OLED MIRROR & ACTUATORS
  // --------------------------------------------------------------------------
  renderOledMirror(state) {
    const norm = state.normalized || {};
    const scores = state.scores || {};
    const read = state.readings || {};

    const linesEl = document.getElementById("oled-lines");
    const statusEl = document.getElementById("oled-status");
    const titleEl = document.getElementById("oled-title");

    if (titleEl) titleEl.textContent = `${state.node_id} [EDGE AI]`;
    if (statusEl) statusEl.textContent = scores.highest_severity === "NORMAL" ? "ENV NORMAL" : `ALERT: ${scores.highest_hazard}`;

    if (linesEl) {
      linesEl.innerHTML = `
        <div>T: ${(norm.temperature_c || 25).toFixed(1)}C  H: ${Math.round(norm.humidity_pct || 50)}%</div>
        <div>P: ${Math.round(norm.pressure_hpa || 1013)}hPa  Soil: ${Math.round(norm.soil_moisture_pct || 30)}%</div>
        <div>Flood: ${scores.flood_severity || 'NORMAL'} (${Math.round(scores.flood_score || 0)})</div>
        <div>Fire:  ${scores.fire_severity || 'NORMAL'} (${Math.round(scores.fire_score || 0)})</div>
      `;
    }

    // Actuator indicators
    const highestSev = scores.highest_severity || "NORMAL";
    const buzzerEl = document.getElementById("act-buzzer");
    const redEl = document.getElementById("act-red");
    const yellowEl = document.getElementById("act-yellow");
    const greenEl = document.getElementById("act-green");

    if (highestSev === "CRITICAL") {
      if (buzzerEl) { buzzerEl.textContent = "ALARM ACTIVE"; buzzerEl.style.color = "#dc2626"; }
      if (redEl) { redEl.textContent = "ON (BLINK)"; redEl.style.color = "#dc2626"; }
      if (yellowEl) { yellowEl.textContent = "OFF"; yellowEl.style.color = "var(--text-muted)"; }
      if (greenEl) { greenEl.textContent = "OFF"; greenEl.style.color = "var(--text-muted)"; }
    } else if (highestSev === "WARNING") {
      if (buzzerEl) { buzzerEl.textContent = "INTERMITTENT"; buzzerEl.style.color = "#ea580c"; }
      if (redEl) { redEl.textContent = "OFF"; redEl.style.color = "var(--text-muted)"; }
      if (yellowEl) { yellowEl.textContent = "ON"; yellowEl.style.color = "#ea580c"; }
      if (greenEl) { greenEl.textContent = "OFF"; greenEl.style.color = "var(--text-muted)"; }
    } else {
      if (buzzerEl) { buzzerEl.textContent = "SILENT"; buzzerEl.style.color = "var(--text-muted)"; }
      if (redEl) { redEl.textContent = "OFF"; redEl.style.color = "var(--text-muted)"; }
      if (yellowEl) { yellowEl.textContent = "OFF"; yellowEl.style.color = "var(--text-muted)"; }
      if (greenEl) { greenEl.textContent = "PULSE 1Hz"; greenEl.style.color = "#16a34a"; }
    }
  }

  // --------------------------------------------------------------------------
  // TIME-SERIES CHARTS (SVG Vector Rendering) — 60-second window
  // --------------------------------------------------------------------------
  pushChartSample(state) {
    const norm   = state.normalized || {};
    const scores = state.scores || {};
    const now    = new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });

    this.chartData.timestamps.push(now);
    this.chartData.water_level.push(norm.water_level_cm || 0);
    this.chartData.rain_intensity.push(norm.rain_intensity_pct || 0);
    this.chartData.mq2_smoke.push(norm.mq2_anomaly_pct || 0);
    this.chartData.temperature.push(norm.temperature_c || 25);
    this.chartData.flood_score.push(scores.flood_score || 0);
    this.chartData.fire_score.push(scores.fire_score || 0);
    this.chartData.industrial_score.push(scores.industrial_score || 0);

    const maxPts = 60; // 60-second ring buffer
    if (this.chartData.timestamps.length > maxPts) {
      for (const k in this.chartData) this.chartData[k].shift();
    }

    this.renderSvgChart("chart-hydro-svg", [
      { data: this.chartData.water_level,    color: "#0284c7", label: "Water Level (cm)",  max: 100 },
      { data: this.chartData.rain_intensity, color: "#06b6d4", label: "Rain Intensity (%)", max: 100 }
    ], null, this.chartData.timestamps);

    this.renderSvgChart("chart-gas-svg", [
      { data: this.chartData.mq2_smoke,   color: "#e11d48", label: "MQ-2 Smoke Anomaly (%)", max: 100 },
      { data: this.chartData.temperature, color: "#d97706", label: "Temperature (°C)",        max: 70 }
    ], null, this.chartData.timestamps);

    this.renderSvgChart("chart-hazard-svg", [
      { data: this.chartData.flood_score,      color: "#0284c7", label: "Flood Risk",       max: 100 },
      { data: this.chartData.fire_score,       color: "#e11d48", label: "Fire Risk",        max: 100 },
      { data: this.chartData.industrial_score, color: "#8b5cf6", label: "Industrial Risk",  max: 100 }
    ], 75.0, this.chartData.timestamps);
  }

  renderSvgChart(svgId, seriesList, thresholdVal = null, timestamps = []) {
    const svg = document.getElementById(svgId);
    if (!svg) return;

    const w     = svg.clientWidth  || 400;
    const h     = svg.clientHeight || 110;
    const padL  = 34; // left padding for Y-axis labels
    const padR  = 6;
    const padT  = 10;
    const padB  = 18; // bottom padding for X-axis time labels
    const chartW = w - padL - padR;
    const chartH = h - padT - padB;

    let svgInner = "";

    // Y-axis gridlines & tick labels at 0, 25, 50, 75, 100
    const yTicks = [0, 25, 50, 75, 100];
    yTicks.forEach(tick => {
      const y = padT + chartH - (tick / 100) * chartH;
      svgInner += `<line x1="${padL}" y1="${y}" x2="${padL + chartW}" y2="${y}" stroke="var(--chart-grid)" stroke-width="${tick === 0 ? 1.5 : 0.8}" stroke-dasharray="${tick === 0 ? '' : '4,3'}"/>`;
      svgInner += `<text x="${padL - 4}" y="${y + 3.5}" text-anchor="end" font-size="8" fill="var(--text-muted)" font-family="JetBrains Mono, monospace">${tick}</text>`;
    });

    // Critical threshold line with label
    if (thresholdVal !== null) {
      const thY = padT + chartH - (thresholdVal / 100) * chartH;
      svgInner += `<line x1="${padL}" y1="${thY}" x2="${padL + chartW}" y2="${thY}" stroke="#dc2626" stroke-dasharray="5,3" stroke-width="1.5"/>`;
      svgInner += `<text x="${padL + chartW - 2}" y="${thY - 2}" text-anchor="end" font-size="8" fill="#dc2626" font-weight="700">⚠ CRITICAL</text>`;
    }

    // X-axis time labels (first, middle, last)
    if (timestamps.length >= 2) {
      const indices = [0, Math.floor(timestamps.length / 2), timestamps.length - 1];
      indices.forEach(i => {
        if (!timestamps[i]) return;
        const x = padL + (i / Math.max(1, timestamps.length - 1)) * chartW;
        svgInner += `<text x="${x}" y="${h - 2}" text-anchor="middle" font-size="8" fill="var(--text-muted)" font-family="JetBrains Mono, monospace">${timestamps[i]}</text>`;
      });
    }

    // Draw series
    seriesList.forEach((series, si) => {
      const pts = series.data;
      if (pts.length < 2) return;

      const stepX = chartW / Math.max(1, pts.length - 1);

      // Build line path
      let pathD = "";
      let areaD = "";
      pts.forEach((val, idx) => {
        const x    = padL + idx * stepX;
        const normY = Math.max(0, Math.min(series.max, val)) / series.max;
        const y    = padT + chartH - normY * chartH;
        if (idx === 0) { pathD += `M ${x} ${y}`; areaD += `M ${x} ${padT + chartH} L ${x} ${y}`; }
        else           { pathD += ` L ${x} ${y}`; areaD += ` L ${x} ${y}`; }
      });
      // Close area
      const lastX = padL + (pts.length - 1) * stepX;
      areaD += ` L ${lastX} ${padT + chartH} Z`;

      // Area fill (semi-transparent)
      svgInner += `<path d="${areaD}" fill="${series.color}" fill-opacity="0.10"/>`;
      // Main line
      svgInner += `<path d="${pathD}" fill="none" stroke="${series.color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`;

      // Current value dot + label at right edge
      const lastVal  = pts[pts.length - 1];
      const lastNormY = Math.max(0, Math.min(series.max, lastVal)) / series.max;
      const dotX     = padL + (pts.length - 1) * stepX;
      const dotY     = padT + chartH - lastNormY * chartH;
      svgInner += `<circle cx="${dotX}" cy="${dotY}" r="3.5" fill="${series.color}" stroke="white" stroke-width="1.5"/>`;
      const labelVal = series.max === 70 ? lastVal.toFixed(1) : Math.round(lastVal);
      const lx = dotX + 5;
      const ly = Math.max(padT + 8, Math.min(padT + chartH - 2, dotY + 3.5));
      svgInner += `<text x="${lx}" y="${ly}" font-size="8" font-weight="700" fill="${series.color}" font-family="JetBrains Mono, monospace">${labelVal}</text>`;
    });

    svg.innerHTML = svgInner;
  }

  // --------------------------------------------------------------------------
  // NOTIFICATION FEED RENDERING
  // --------------------------------------------------------------------------
  fetchAndRenderNotifications() {
    fetch(`/api/notifications?tier=${this.selectedNotificationTier}`)
      .then(r => r.json())
      .then(data => {
        this.renderNotificationList(data.notifications || []);
      })
      .catch(() => {});
  }

  renderNotificationFeed(activeAlerts) {
    if (this.selectedNotificationTier === "ALL") {
      this.renderNotificationList(activeAlerts);
    } else {
      const filtered = activeAlerts.filter(a => (a.notification_tier || "CITIZEN").toUpperCase() === this.selectedNotificationTier);
      this.renderNotificationList(filtered);
    }
  }

  renderNotificationList(alerts) {
    const container = document.getElementById("notification-feed-container");
    if (!container) return;

    if (!alerts || alerts.length === 0) {
      container.innerHTML = `<div style="text-align:center; padding:12px; color:var(--text-muted); font-size:11px;">No active notifications in this category.</div>`;
      return;
    }

    let html = "";
    alerts.forEach(a => {
      const tier = (a.notification_tier || "CITIZEN").toUpperCase();
      const reasons = a.reasons || [];
      const reasonText = reasons.join(" • ");

      html += `
        <div class="notif-item tier-${tier}">
          <div class="notif-header">
            <span>${a.title || 'HAZARD ALERT'}</span>
            <span class="notif-tier-badge">${tier}</span>
          </div>
          <div class="notif-body">
            <div><strong>Node:</strong> ${a.node_id} | <strong>Score:</strong> ${Math.round(a.score)}/100</div>
            <div>${reasonText}</div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  }

  // --------------------------------------------------------------------------
  // CLOCK HELPER
  // --------------------------------------------------------------------------
  updateClock() {
    const el = document.getElementById("system-clock");
    if (el) {
      const now = new Date();
      el.textContent = now.toTimeString().split(" ")[0] + " LOCAL";
    }
  }

  // --------------------------------------------------------------------------
  // DESKTOP NOTIFICATIONS (Windows 10/11 via Web Notifications API)
  // --------------------------------------------------------------------------
  _requestNotificationPermission() {
    if (!("Notification" in window)) return;
    if (Notification.permission === "granted") {
      this.desktopNotifEnabled = true;
    } else if (Notification.permission !== "denied") {
      Notification.requestPermission().then(perm => {
        this.desktopNotifEnabled = perm === "granted";
        if (this.desktopNotifEnabled) {
          this._showToast("🔔 Desktop notifications enabled for critical alerts.", "success");
        }
      });
    }
  }

  _fireDesktopNotification(alert) {
    if (!this.alarmActive) return;
    const key     = `${alert.node_id}-${alert.hazard_type}`;
    const now     = Date.now();
    const cooldown = 60000; // 60-second cooldown per alert type per node
    if (this.notificationCooldowns[key] && now - this.notificationCooldowns[key] < cooldown) return;
    this.notificationCooldowns[key] = now;

    const body = `${alert.node_id} — Score: ${Math.round(alert.score)}/100\n${(alert.reasons || [])[0] || ""}`;
    const icon = alert.hazard_type === "FLOOD" ? "🌊" :
                 alert.hazard_type === "FIRE"  ? "🔥" :
                 alert.hazard_type === "INDUSTRIAL" ? "🏭" : "⚠️";

    if (this.desktopNotifEnabled) {
      try {
        new Notification(`${icon} EIN CRITICAL ALERT — ${alert.hazard_type}`, {
          body: body,
          icon: null,
          requireInteraction: false,
          silent: false
        });
      } catch (e) { /* fallback to in-app toast */ }
    }
    // Always show in-app toast for control room visibility
    this._showToast(`${icon} <strong>${alert.hazard_type} CRITICAL</strong> — ${alert.node_id} (${Math.round(alert.score)}/100)`, "danger");
  }

  _ensureToastContainer() {
    if (document.getElementById("toast-container")) return;
    const c = document.createElement("div");
    c.id = "toast-container";
    c.style.cssText = "position:fixed;bottom:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none;";
    document.body.appendChild(c);
  }

  _showToast(html, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const colors = { danger: "#dc2626", warn: "#ea580c", success: "#16a34a", info: "#0284c7" };
    const bg     = colors[type] || colors.info;

    const toast = document.createElement("div");
    toast.style.cssText = `background:${bg};color:#fff;padding:10px 16px;border-radius:8px;font-size:13px;font-family:Inter,sans-serif;font-weight:500;max-width:320px;box-shadow:0 4px 20px rgba(0,0,0,0.3);pointer-events:auto;opacity:1;transition:opacity 0.4s;`;
    toast.innerHTML = html;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 450);
    }, 5000);
  }
}

function jsonStringifySafe(obj) {
  try {
    return JSON.stringify(obj);
  } catch (e) {
    return "{}";
  }
}

// Instantiate global app on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  window.app = new DashboardApp();
});
