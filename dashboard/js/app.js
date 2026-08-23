/**
 * Environmental Monitoring Command Center
 * Real EAS (Emergency Alert System) Multi-Category Audio Engine
 */

class SoundAlertManager {
  constructor() {
    this.audioCtx = null;
    this.isAlarmEnabled = localStorage.getItem("sih_alarm_enabled") !== "false"; // Default: true (ON)
    this.isSilenced = false;
    this.currentAlertLevel = "NORMAL"; // NORMAL | WARNING | CRITICAL
    this.activeAudioElement = null;
    this.sirenLoopTimer = null;

    // Sound file endpoints for each hazard category
    this.soundPaths = {
      WARNING: "sounds/eas_warning.wav",
      FLOOD: "sounds/eas_flood.wav",
      FIRE: "sounds/eas_fire.wav",
      POLLUTION: "sounds/eas_gas.wav"
    };
  }

  initAudioContext() {
    if (!this.audioCtx) {
      const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
      if (AudioCtxClass) {
        this.audioCtx = new AudioCtxClass();
      }
    }
    if (this.audioCtx && this.audioCtx.state === "suspended") {
      this.audioCtx.resume();
    }
  }

  toggleAlarm() {
    this.isAlarmEnabled = !this.isAlarmEnabled;
    localStorage.setItem("sih_alarm_enabled", this.isAlarmEnabled ? "true" : "false");
    if (!this.isAlarmEnabled) {
      this.stopAlarm();
    } else {
      this.initAudioContext();
      this.playWarningSound(); // Test sound on activation
    }
    return this.isAlarmEnabled;
  }

  silenceTemporary() {
    this.isSilenced = true;
    this.stopAlarm();
  }

  updateAlertState(highestSeverity, activeHazardType = "FLOOD") {
    if (highestSeverity === this.currentAlertLevel) return;
    this.currentAlertLevel = highestSeverity;

    if (highestSeverity === "CRITICAL") {
      this.isSilenced = false;
      this.startCriticalAlarm(activeHazardType);
    } else if (highestSeverity === "WARNING") {
      this.stopAlarm();
      if (this.isAlarmEnabled && !this.isSilenced) {
        this.playWarningSound();
      }
    } else {
      this.stopAlarm();
      this.isSilenced = false;
    }
  }

  playWarningSound() {
    if (!this.isAlarmEnabled || this.isSilenced) return;
    this.playSoundFile(this.soundPaths.WARNING, () => {
      // Synthesis fallback if file is loading
      this.playSynthEASTone(853.0, 960.0, 0.7);
    });
  }

  startCriticalAlarm(hazardType = "FLOOD") {
    this.stopAlarm();
    if (!this.isAlarmEnabled || this.isSilenced) return;
    this.initAudioContext();

    const path = this.soundPaths[hazardType] || this.soundPaths.FLOOD;

    const playLoop = () => {
      if (!this.isAlarmEnabled || this.isSilenced) {
        this.stopAlarm();
        return;
      }
      this.playSoundFile(path, () => {
        // Synthesis fallback
        this.playSynthEASAlarm(hazardType);
      });
    };

    playLoop();
    this.sirenLoopTimer = setInterval(playLoop, 4500);
  }

  playSoundFile(src, fallbackFn) {
    try {
      const audio = new Audio(src);
      audio.volume = 0.55;
      const playPromise = audio.play();
      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            this.activeAudioElement = audio;
          })
          .catch(() => {
            if (fallbackFn) fallbackFn();
          });
      }
    } catch (e) {
      if (fallbackFn) fallbackFn();
    }
  }

  /**
   * High-Fidelity Web Audio EAS Dual-Tone Synthesizer Fallback
   */
  playSynthEASTone(f1 = 853.0, f2 = 960.0, duration = 0.8) {
    if (!this.isAlarmEnabled || !this.audioCtx) return;
    try {
      const now = this.audioCtx.currentTime;
      const osc1 = this.audioCtx.createOscillator();
      const osc2 = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();

      osc1.type = "sine";
      osc1.frequency.setValueAtTime(f1, now);
      osc2.type = "sine";
      osc2.frequency.setValueAtTime(f2, now);

      gain.gain.setValueAtTime(0.18, now);
      gain.gain.setValueAtTime(0.18, now + duration - 0.05);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);

      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(this.audioCtx.destination);

      osc1.start(now);
      osc2.start(now);
      osc1.stop(now + duration);
      osc2.stop(now + duration);
    } catch (e) {}
  }

  playSynthEASAlarm(hazardType) {
    this.playSynthEASTone(853.0, 960.0, 1.0);
  }

  stopAlarm() {
    if (this.sirenLoopTimer) {
      clearInterval(this.sirenLoopTimer);
      this.sirenLoopTimer = null;
    }
    if (this.activeAudioElement) {
      try {
        this.activeAudioElement.pause();
        this.activeAudioElement.currentTime = 0;
      } catch (e) {}
      this.activeAudioElement = null;
    }
  }
}

class ThemeManager {
  constructor() {
    this.currentTheme = localStorage.getItem("sih_theme") || "light"; // Default: light
    this.applyTheme(this.currentTheme);
  }

  applyTheme(theme) {
    this.currentTheme = theme;
    localStorage.setItem("sih_theme", theme);
    document.body.className = `theme-${theme}`;

    document.querySelectorAll(".theme-btn").forEach((btn) => {
      if (btn.getAttribute("data-theme") === theme) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });
  }
}

class AuthManager {
  constructor(onAuthSuccess) {
    this.onAuthSuccess = onAuthSuccess;
    this.modalEl = document.getElementById("login-modal");
    this.formEl = document.getElementById("login-form");
    this.userInput = document.getElementById("input-username");
    this.passInput = document.getElementById("input-password");
    this.errorEl = document.getElementById("login-error");
    this.userNameStat = document.getElementById("stat-user-name");
    this.btnLogout = document.getElementById("btn-logout");

    this.checkExistingSession();
    this.bindEvents();
  }

  checkExistingSession() {
    const sessionUser = sessionStorage.getItem("sih_auth_user");
    if (sessionUser) {
      this.modalEl.classList.add("hidden");
      this.userNameStat.textContent = sessionUser;
      if (this.onAuthSuccess) this.onAuthSuccess(sessionUser);
    } else {
      this.modalEl.classList.remove("hidden");
    }
  }

  bindEvents() {
    this.formEl.addEventListener("submit", (e) => {
      e.preventDefault();
      const u = this.userInput.value.trim();
      const p = this.passInput.value.trim();

      // Accepted credentials
      if ((u === "admin" && (p === "admin123" || p === "sih2026")) ||
          (u === "operator" && (p === "operator123" || p === "sih2026")) ||
          (u.length >= 3 && p.length >= 4)) {
        sessionStorage.setItem("sih_auth_user", u);
        this.userNameStat.textContent = u;
        this.errorEl.classList.add("hidden");
        this.modalEl.classList.add("hidden");
        if (this.onAuthSuccess) this.onAuthSuccess(u);
      } else {
        this.errorEl.classList.remove("hidden");
      }
    });

    this.btnLogout.addEventListener("click", () => {
      sessionStorage.removeItem("sih_auth_user");
      this.modalEl.classList.remove("hidden");
      this.userInput.value = "";
      this.passInput.value = "";
    });
  }
}

class CommandCenterApp {
  constructor() {
    this.selectedNodeId = "NODE_001";
    this.latestStates = {};
    this.historyData = {
      NODE_001: [],
      NODE_002: [],
      NODE_003: [],
      NODE_004: []
    };
    this.activeScenario = "NORMAL";
    this.targetNode = "NODE_001";
    this.sseConnected = false;

    this.soundManager = new SoundAlertManager();
    this.themeManager = new ThemeManager();
    this.authManager = new AuthManager((user) => {
      this.soundManager.initAudioContext();
    });

    this.initElements();
    this.bindEvents();
    this.startDataStream();
    this.startClock();
    this.updateAlarmButtonState();
  }

  initElements() {
    // Emergency Banner
    this.emergencyBannerEl = document.getElementById("emergency-banner");
    this.emergencyTitleEl = document.getElementById("emergency-title");
    this.emergencyDescEl = document.getElementById("emergency-desc");
    this.emergencyActionEl = document.getElementById("emergency-action");
    this.btnSilenceAlarm = document.getElementById("btn-silence-alarm");

    // Master Alarm Button
    this.btnAlarmToggle = document.getElementById("btn-alarm-toggle");
    this.alarmIconEl = document.getElementById("alarm-icon");
    this.alarmTextEl = document.getElementById("alarm-text");

    // Top bar elements
    this.clockEl = document.getElementById("system-clock");
    this.totalNodesEl = document.getElementById("stat-total-nodes");
    this.onlineNodesEl = document.getElementById("stat-online-nodes");
    this.activeAlertsEl = document.getElementById("stat-active-alerts");
    this.maxHazardEl = document.getElementById("stat-max-hazard");
    this.connStatusEl = document.getElementById("stat-conn-status");
    this.badgeAlertCount = document.getElementById("badge-alert-count");
    this.activeNodeNameEl = document.getElementById("active-node-name");

    // Node selector container
    this.nodeListContainer = document.getElementById("node-list-container");

    // Hazard card elements
    this.floodScoreEl = document.getElementById("score-flood-val");
    this.floodBadgeEl = document.getElementById("badge-flood");
    this.floodFillEl = document.getElementById("fill-flood");
    this.floodReasonsEl = document.getElementById("factors-flood");

    this.fireScoreEl = document.getElementById("score-fire-val");
    this.fireBadgeEl = document.getElementById("badge-fire");
    this.fireFillEl = document.getElementById("fill-fire");
    this.fireReasonsEl = document.getElementById("factors-fire");

    this.pollutionScoreEl = document.getElementById("score-pollution-val");
    this.pollutionBadgeEl = document.getElementById("badge-pollution");
    this.pollutionFillEl = document.getElementById("fill-pollution");
    this.pollutionReasonsEl = document.getElementById("factors-pollution");

    // OLED Virtual Mirror
    this.oledTitleEl = document.getElementById("oled-title");
    this.oledStatusEl = document.getElementById("oled-status");
    this.oledLinesEl = document.getElementById("oled-lines");
    this.actBuzzerEl = document.getElementById("act-buzzer");
    this.actRedEl = document.getElementById("act-red");
    this.actYellowEl = document.getElementById("act-yellow");
    this.actGreenEl = document.getElementById("act-green");

    // Telemetry cells
    this.valTempEl = document.getElementById("tel-temp-val");
    this.valHumEl = document.getElementById("tel-hum-val");
    this.valPresEl = document.getElementById("tel-pres-val");
    this.valGasResEl = document.getElementById("tel-gasres-val");
    this.valMq2El = document.getElementById("tel-mq2-val");
    this.valMq7El = document.getElementById("tel-mq7-val");
    this.valRainEl = document.getElementById("tel-rain-val");
    this.valWaterEl = document.getElementById("tel-water-val");
    this.valWaterRateEl = document.getElementById("tel-waterrate-val");
    this.valFlameEl = document.getElementById("tel-flame-val");
    this.valBatteryEl = document.getElementById("tel-battery-val");
    this.valRssiEl = document.getElementById("tel-rssi-val");

    // Health tags
    this.healthBmeEl = document.getElementById("health-bme");
    this.healthMq2El = document.getElementById("health-mq2");
    this.healthMq7El = document.getElementById("health-mq7");
    this.healthRainEl = document.getElementById("health-rain");
    this.healthWaterEl = document.getElementById("health-water");
    this.healthFlameEl = document.getElementById("health-flame");

    // Alert & Event Feed
    this.alertFeedEl = document.getElementById("alert-feed-container");

    // Charts SVG
    this.chartHydroSvg = document.getElementById("chart-hydro-svg");
    this.chartGasSvg = document.getElementById("chart-gas-svg");
    this.chartHazardSvg = document.getElementById("chart-hazard-svg");

    // Node Map SVG
    this.mapSvg = document.getElementById("node-map-svg");

    // Reset button
    this.btnResetNormal = document.getElementById("btn-reset-normal");
  }

  bindEvents() {
    // Theme switcher buttons
    document.querySelectorAll(".theme-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const theme = btn.getAttribute("data-theme");
        this.themeManager.applyTheme(theme);
      });
    });

    // Master Alarm toggle button
    this.btnAlarmToggle.addEventListener("click", () => {
      this.soundManager.toggleAlarm();
      this.updateAlarmButtonState();
    });

    // Temporary silence button on emergency banner
    this.btnSilenceAlarm.addEventListener("click", () => {
      this.soundManager.silenceTemporary();
      this.btnSilenceAlarm.textContent = "✓ Silenced";
    });

    // Reset scenario button
    if (this.btnResetNormal) {
      this.btnResetNormal.addEventListener("click", () => {
        this.triggerScenario("NORMAL");
      });
    }

    // Scenario buttons
    document.querySelectorAll(".scenario-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        this.soundManager.initAudioContext();
        const scenario = btn.getAttribute("data-scenario");
        this.triggerScenario(scenario);
      });
    });

    // Unlock Web Audio on first user interaction
    document.body.addEventListener(
      "click",
      () => {
        this.soundManager.initAudioContext();
      },
      { once: true }
    );
  }

  updateAlarmButtonState() {
    if (this.soundManager.isAlarmEnabled) {
      this.btnAlarmToggle.className = "alarm-master-btn active";
      this.alarmIconEl.textContent = "🚨";
      this.alarmTextEl.textContent = "ALARM: ON";
    } else {
      this.btnAlarmToggle.className = "alarm-master-btn off";
      this.alarmIconEl.textContent = "🔕";
      this.alarmTextEl.textContent = "ALARM: OFF";
    }
  }

  startClock() {
    const update = () => {
      const now = new Date();
      this.clockEl.textContent = now.toISOString().replace("T", " ").substring(0, 19) + " UTC";
    };
    update();
    setInterval(update, 1000);
  }

  startDataStream() {
    this.fetchOverview();

    // Server-Sent Events (SSE)
    if (!!window.EventSource) {
      const source = new EventSource("/api/stream");

      source.onopen = () => {
        this.sseConnected = true;
        this.connStatusEl.innerHTML = `<span class="live-pulse"></span> LIVE SSE`;
      };

      source.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleLiveUpdate(data);
        } catch (e) {
          console.error("SSE parse error", e);
        }
      };

      source.onerror = () => {
        this.sseConnected = false;
        this.connStatusEl.innerHTML = `<span style="color:#f59e0b">● POLLING</span>`;
      };
    }

    // Fallback polling interval (1.5s)
    setInterval(() => {
      if (!this.sseConnected) {
        this.fetchOverview();
      }
    }, 1500);
  }

  async fetchOverview() {
    try {
      const res = await fetch("/api/overview");
      if (res.ok) {
        const data = await res.json();
        this.handleLiveUpdate(data);
      }
    } catch (e) {
      console.warn("Fetch overview failed:", e);
    }
  }

  handleLiveUpdate(data) {
    this.latestStates = data.latest_states || {};
    this.activeScenario = data.active_scenario || "NORMAL";
    this.targetNode = data.target_node || "NODE_001";

    // 1. Update Header stats
    this.totalNodesEl.textContent = data.total_nodes || 4;
    this.onlineNodesEl.textContent = data.online_nodes || 0;
    this.activeAlertsEl.textContent = data.active_alerts_count || 0;
    this.badgeAlertCount.textContent = `${data.active_alerts_count || 0} ACTIVE`;

    if (data.active_alerts_count > 0) {
      this.activeAlertsEl.parentElement.className = "metric-pill alert";
    } else {
      this.activeAlertsEl.parentElement.className = "metric-pill healthy";
    }

    const maxScore = data.highest_hazard_score || 0;
    const maxType = data.highest_hazard_type || "NONE";
    this.maxHazardEl.textContent = `${maxType} (${maxScore})`;
    if (maxScore >= 75) {
      this.maxHazardEl.parentElement.className = "metric-pill alert";
    } else if (maxScore >= 50) {
      this.maxHazardEl.parentElement.className = "metric-pill warning";
    } else {
      this.maxHazardEl.parentElement.className = "metric-pill healthy";
    }

    // 2. EAS Sound & Emergency Banner Logic
    const highestOverallSev = maxScore >= 75 ? "CRITICAL" : (maxScore >= 50 ? "WARNING" : "NORMAL");
    this.soundManager.updateAlertState(highestOverallSev, maxType);
    this.updateEmergencyBanner(data.active_alerts || [], highestOverallSev);

    // 3. Render Node Selector Tabs
    this.renderNodeSelector(data.nodes || []);

    // 4. Render Selected Node Data
    const currentNodeData = this.latestStates[this.selectedNodeId];
    if (currentNodeData) {
      this.activeNodeNameEl.textContent = `${this.selectedNodeId}`;
      this.appendHistory(this.selectedNodeId, currentNodeData);
      this.renderHazardMatrix(currentNodeData.scores, currentNodeData.anomaly_stats);
      this.renderTelemetryGrid(currentNodeData.readings, currentNodeData.normalized, currentNodeData.anomaly_stats);
      this.renderOledMirror(currentNodeData.readings, currentNodeData.scores);
      this.renderCharts(this.selectedNodeId);
    }

    // 5. Render Alert Feed
    this.renderAlertFeed(data.active_alerts || []);

    // 6. Render Node Map
    this.renderNodeMap(data.nodes || []);

    // 7. Update Scenario active buttons
    document.querySelectorAll(".scenario-btn").forEach((btn) => {
      const sc = btn.getAttribute("data-scenario");
      if (sc === this.activeScenario) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });
  }

  updateEmergencyBanner(alerts, highestSev) {
    if (highestSev === "CRITICAL" && alerts.length > 0) {
      const critAlert = alerts.find((a) => a.severity === "CRITICAL") || alerts[0];
      this.emergencyBannerEl.classList.remove("hidden");
      this.emergencyTitleEl.textContent = `🚨 EAS CRITICAL ALERT: ${critAlert.title} (${critAlert.node_id} • Score: ${Math.round(critAlert.score)}/100)`;
      this.emergencyDescEl.textContent = (critAlert.reasons && critAlert.reasons[0]) || "Emergency alert system broadcast: threat parameters exceeding critical limits.";

      if (critAlert.hazard_type === "FLOOD") {
        this.emergencyActionEl.textContent = "ACTION: EVACUATE LOW GROUND & WATER CHANNELS";
      } else if (critAlert.hazard_type === "FIRE") {
        this.emergencyActionEl.textContent = "ACTION: SOUND WILDFIRE SIREN & DISPATCH SUPPRESSION";
      } else {
        this.emergencyActionEl.textContent = "ACTION: EVACUATE VENTILATION ZONE";
      }
      this.btnSilenceAlarm.textContent = "🔕 Silence Alarm";
    } else {
      this.emergencyBannerEl.classList.add("hidden");
    }
  }

  appendHistory(nodeId, state) {
    const list = this.historyData[nodeId] || [];
    list.push({
      time: new Date(),
      water: state.normalized.water_level_cm,
      rain: state.normalized.rain_intensity_pct,
      temp: state.normalized.temperature_c,
      mq2: state.normalized.mq2_anomaly_pct,
      mq7: state.normalized.mq7_anomaly_pct,
      flood: state.scores.flood_score,
      fire: state.scores.fire_score,
      pollution: state.scores.pollution_score
    });
    if (list.length > 30) list.shift();
    this.historyData[nodeId] = list;
  }

  renderNodeSelector(nodes) {
    this.nodeListContainer.innerHTML = "";
    nodes.forEach((node) => {
      const isActive = node.node_id === this.selectedNodeId;
      const btn = document.createElement("button");
      btn.className = `node-btn ${isActive ? "active" : ""}`;
      btn.onclick = () => {
        this.selectedNodeId = node.node_id;
        const currentData = this.latestStates[this.selectedNodeId];
        if (currentData) {
          this.renderHazardMatrix(currentData.scores, currentData.anomaly_stats);
          this.renderTelemetryGrid(currentData.readings, currentData.normalized, currentData.anomaly_stats);
          this.renderOledMirror(currentData.readings, currentData.scores);
          this.renderCharts(this.selectedNodeId);
        }
        this.renderNodeSelector(nodes);
      };

      const statusClass = node.status === "ONLINE" ? "sev-NORMAL" : (node.status === "DEGRADED" ? "sev-WARNING" : "sev-CRITICAL");
      const highestScore = node.latest_scores ? node.latest_scores.highest_score : 0;
      const highestSev = node.latest_scores ? node.latest_scores.highest_severity : "NORMAL";

      btn.innerHTML = `
        <div class="node-btn-header">
          <span class="node-btn-id">${node.node_id}</span>
          <span class="node-btn-status ${statusClass}">${node.status}</span>
        </div>
        <div class="node-btn-zone">${node.name}</div>
        <div style="margin-top:4px; display:flex; justify-content:space-between; font-size:10px; color:var(--text-muted);">
          <span>Risk: <b style="color:${this.getSeverityColor(highestSev)}">${highestScore}</b></span>
          <span>🔋 ${node.battery_voltage.toFixed(1)}V • 📶 ${node.signal_strength}dBm</span>
        </div>
      `;
      this.nodeListContainer.appendChild(btn);
    });
  }

  getSeverityColor(sev) {
    switch (sev) {
      case "CRITICAL": return "var(--sev-critical-text)";
      case "WARNING": return "var(--sev-warning-text)";
      case "LOW": return "var(--sev-low-text)";
      default: return "var(--sev-normal-text)";
    }
  }

  renderHazardMatrix(scores, stats) {
    if (!scores) return;

    // 1. Flood Card
    this.floodScoreEl.textContent = Math.round(scores.flood_score);
    this.floodScoreEl.style.color = this.getSeverityColor(scores.flood_severity);
    this.floodBadgeEl.textContent = `[${this.getSeveritySymbol(scores.flood_severity)} ${scores.flood_severity}]`;
    this.floodBadgeEl.className = `severity-badge sev-${scores.flood_severity}`;
    this.floodFillEl.style.width = `${scores.flood_score}%`;
    this.floodFillEl.style.backgroundColor = this.getSeverityColor(scores.flood_severity);
    this.renderFactorList(this.floodReasonsEl, scores.flood_reasons);

    // 2. Fire Card
    this.fireScoreEl.textContent = Math.round(scores.fire_score);
    this.fireScoreEl.style.color = this.getSeverityColor(scores.fire_severity);
    this.fireBadgeEl.textContent = `[${this.getSeveritySymbol(scores.fire_severity)} ${scores.fire_severity}]`;
    this.fireBadgeEl.className = `severity-badge sev-${scores.fire_severity}`;
    this.fireFillEl.style.width = `${scores.fire_score}%`;
    this.fireFillEl.style.backgroundColor = this.getSeverityColor(scores.fire_severity);
    this.renderFactorList(this.fireReasonsEl, scores.fire_reasons);

    // 3. Pollution Card
    this.pollutionScoreEl.textContent = Math.round(scores.pollution_score);
    this.pollutionScoreEl.style.color = this.getSeverityColor(scores.pollution_severity);
    this.pollutionBadgeEl.textContent = `[${this.getSeveritySymbol(scores.pollution_severity)} ${scores.pollution_severity}]`;
    this.pollutionBadgeEl.className = `severity-badge sev-${scores.pollution_severity}`;
    this.pollutionFillEl.style.width = `${scores.pollution_score}%`;
    this.pollutionFillEl.style.backgroundColor = this.getSeverityColor(scores.pollution_severity);
    this.renderFactorList(this.pollutionReasonsEl, scores.pollution_reasons);
  }

  getSeveritySymbol(sev) {
    switch (sev) {
      case "CRITICAL": return "!";
      case "WARNING": return "▲";
      case "LOW": return "ℹ";
      default: return "✓";
    }
  }

  renderFactorList(container, reasons) {
    if (!reasons || reasons.length === 0) {
      container.innerHTML = `<div class="factor-item"><span class="factor-name">• Baseline nominal</span></div>`;
      return;
    }
    let html = "";
    reasons.slice(0, 3).forEach((r) => {
      html += `<div class="factor-item"><span class="factor-name">• ${r}</span></div>`;
    });
    container.innerHTML = html;
  }

  renderTelemetryGrid(raw, norm, stats) {
    if (!norm) return;

    this.valTempEl.textContent = norm.temperature_c.toFixed(1);
    this.valHumEl.textContent = norm.humidity_pct.toFixed(0);
    this.valPresEl.textContent = norm.pressure_hpa.toFixed(0);
    this.valGasResEl.textContent = (norm.gas_resistance_ohms / 1000.0).toFixed(1);

    this.valMq2El.textContent = `${raw.mq2_raw}`;
    document.getElementById("tel-mq2-pct").textContent = `Anomaly: ${norm.mq2_anomaly_pct.toFixed(0)}%`;

    this.valMq7El.textContent = `${raw.mq7_raw}`;
    document.getElementById("tel-mq7-pct").textContent = `Anomaly: ${norm.mq7_anomaly_pct.toFixed(0)}%`;

    this.valRainEl.textContent = `${norm.rain_intensity_pct.toFixed(0)}%`;
    this.valWaterEl.textContent = `${norm.water_level_cm.toFixed(1)}`;
    this.valWaterRateEl.textContent = `${norm.water_rate_of_rise_cm_min >= 0 ? "+" : ""}${norm.water_rate_of_rise_cm_min.toFixed(1)} cm/m`;

    this.valFlameEl.textContent = norm.flame_detected ? "DETECTED !" : "CLEAR";
    this.valFlameEl.style.color = norm.flame_detected ? "var(--sev-critical-text)" : "var(--sev-normal-text)";

    this.valBatteryEl.textContent = `${norm.battery_voltage.toFixed(2)} V`;
    this.valRssiEl.textContent = `${norm.signal_strength} dBm`;

    this.setHealthBadge(this.healthBmeEl, norm.health_bme680);
    this.setHealthBadge(this.healthMq2El, norm.health_mq2);
    this.setHealthBadge(this.healthMq7El, norm.health_mq7);
    this.setHealthBadge(this.healthRainEl, norm.health_rain);
    this.setHealthBadge(this.healthWaterEl, norm.health_ultrasonic);
    this.setHealthBadge(this.healthFlameEl, norm.health_flame);
  }

  setHealthBadge(el, health) {
    el.textContent = health;
    el.className = `cell-health ${health}`;
  }

  renderOledMirror(raw, scores) {
    if (!scores) return;

    const highest = scores.highest_severity;
    this.oledTitleEl.textContent = `[SSD1306 128x64] ${this.selectedNodeId}`;

    let linesHtml = "";
    if (highest === "CRITICAL") {
      if (scores.flood_severity === "CRITICAL") {
        this.oledStatusEl.textContent = "! CRITICAL FLOOD !";
        linesHtml = `
          <div>FLOOD RISK: <b>${Math.round(scores.flood_score)} / 100</b></div>
          <div>WATER LEVEL: <b>${raw.water_level_cm.toFixed(1)} cm</b></div>
          <div>RATE OF RISE: <b>+${raw.water_rate_of_rise_cm_min.toFixed(1)} cm/m</b></div>
          <div style="color:#ef4444; margin-top:2px;">ACTION: EVACUATE LOW GROUND</div>
        `;
      } else if (scores.fire_severity === "CRITICAL") {
        this.oledStatusEl.textContent = "! CRITICAL FIRE !";
        linesHtml = `
          <div>FIRE RISK: <b>${Math.round(scores.fire_score)} / 100</b></div>
          <div>FLAME SENSOR: <b>${raw.flame_detected ? "DETECTED!" : "NO"}</b></div>
          <div>TEMP: <b>${raw.temperature.toFixed(1)} C</b> | SMOKE: <b>${raw.mq2_raw}</b></div>
          <div style="color:#ef4444; margin-top:2px;">ACTION: SOUND FIRE ALARM</div>
        `;
      } else {
        this.oledStatusEl.textContent = "! CRITICAL POLLUTION !";
        linesHtml = `
          <div>POLLUTION: <b>${Math.round(scores.pollution_score)} / 100</b></div>
          <div>CO RAW: <b>${raw.mq7_raw}</b> | VOC: <b>${(raw.gas_resistance / 1000).toFixed(0)}k</b></div>
          <div style="color:#ef4444; margin-top:2px;">ACTION: VENTILATE AREA</div>
        `;
      }

      this.actBuzzerEl.textContent = "ALARM ON (150ms)";
      this.actBuzzerEl.style.color = "var(--sev-critical-text)";
      this.actRedEl.textContent = "SOLID ON";
      this.actRedEl.style.color = "var(--sev-critical-text)";
      this.actYellowEl.textContent = "OFF";
      this.actYellowEl.style.color = "var(--text-muted)";
      this.actGreenEl.textContent = "OFF";
      this.actGreenEl.style.color = "var(--text-muted)";

    } else if (highest === "WARNING") {
      this.oledStatusEl.textContent = "--- WARNING ---";
      linesHtml = `
        <div>HAZARD: <b>${scores.highest_hazard} (${Math.round(scores.highest_score)})</b></div>
        <div>T: <b>${raw.temperature.toFixed(1)} C</b> | H: <b>${raw.humidity.toFixed(0)} %</b></div>
        <div>W: <b>${raw.water_level_cm.toFixed(1)} cm</b> | R: <b>${raw.rain_raw < 2000 ? "HIGH" : "LOW"}</b></div>
      `;

      this.actBuzzerEl.textContent = "CHIRP 2s";
      this.actBuzzerEl.style.color = "var(--sev-warning-text)";
      this.actRedEl.textContent = "OFF";
      this.actRedEl.style.color = "var(--text-muted)";
      this.actYellowEl.textContent = "SOLID ON";
      this.actYellowEl.style.color = "var(--sev-warning-text)";
      this.actGreenEl.textContent = "OFF";
      this.actGreenEl.style.color = "var(--text-muted)";

    } else {
      this.oledStatusEl.textContent = "ENVIRONMENT NORMAL";
      linesHtml = `
        <div>T: <b>${raw.temperature.toFixed(1)} C</b>  H: <b>${raw.humidity.toFixed(0)} %</b></div>
        <div>P: <b>${raw.pressure.toFixed(0)} hPa</b></div>
        <div>Flood: <b>LOW (${Math.round(scores.flood_score)})</b></div>
        <div>Fire:  <b>LOW (${Math.round(scores.fire_score)})</b></div>
      `;

      this.actBuzzerEl.textContent = "SILENT";
      this.actBuzzerEl.style.color = "var(--text-muted)";
      this.actRedEl.textContent = "OFF";
      this.actRedEl.style.color = "var(--text-muted)";
      this.actYellowEl.textContent = "OFF";
      this.actYellowEl.style.color = "var(--text-muted)";
      this.actGreenEl.textContent = "PULSE 1Hz";
      this.actGreenEl.style.color = "var(--sev-normal-text)";
    }

    this.oledLinesEl.innerHTML = linesHtml;
  }

  renderCharts(nodeId) {
    const history = this.historyData[nodeId] || [];
    if (history.length < 2) return;

    // 1. Hydrology chart
    this.drawDualChart(
      this.chartHydroSvg,
      history.map((h) => h.water),
      history.map((h) => h.rain),
      "#0284c7",
      "#06b6d4",
      "Depth (cm)",
      "Rain (%)",
      100
    );

    // 2. Combustion & Heat chart
    this.drawDualChart(
      this.chartGasSvg,
      history.map((h) => h.mq2),
      history.map((h) => h.temp),
      "#e11d48",
      "#d97706",
      "Smoke (%)",
      "Temp (°C)",
      100
    );

    // 3. Multi-Hazard risk timeline
    this.drawTripleChart(
      this.chartHazardSvg,
      history.map((h) => h.flood),
      history.map((h) => h.fire),
      history.map((h) => h.pollution),
      "#0284c7",
      "#e11d48",
      "#7c3aed",
      100
    );
  }

  drawDualChart(svg, series1, series2, color1, color2, label1, label2, maxVal = 100) {
    const width = 450;
    const height = 95;
    const padding = 12;

    const points1 = this.createSvgPath(series1, width, height, padding, maxVal);
    const points2 = this.createSvgPath(series2, width, height, padding, maxVal);

    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.innerHTML = `
      <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="var(--border-subtle)" stroke-width="1"/>
      <line x1="${padding}" y1="${padding}" x2="${width - padding}" y2="${padding}" stroke="var(--border-subtle)" stroke-dasharray="2,2" stroke-width="1"/>
      <path d="${points1}" fill="none" stroke="${color1}" stroke-width="2"/>
      <path d="${points2}" fill="none" stroke="${color2}" stroke-width="1.5" stroke-dasharray="3,3"/>
    `;
  }

  drawTripleChart(svg, s1, s2, s3, c1, c2, c3, maxVal = 100) {
    const width = 450;
    const height = 95;
    const padding = 12;

    const p1 = this.createSvgPath(s1, width, height, padding, maxVal);
    const p2 = this.createSvgPath(s2, width, height, padding, maxVal);
    const p3 = this.createSvgPath(s3, width, height, padding, maxVal);

    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.innerHTML = `
      <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="var(--border-subtle)" stroke-width="1"/>
      <line x1="${padding}" y1="${padding}" x2="${width - padding}" y2="${padding}" stroke="var(--border-subtle)" stroke-dasharray="2,2" stroke-width="1"/>
      <!-- Critical line at 75 -->
      <line x1="${padding}" y1="${height - padding - (55 * (height - 2 * padding) / 100)}" x2="${width - padding}" y2="${height - padding - (55 * (height - 2 * padding) / 100)}" stroke="#e11d48" stroke-width="1" stroke-dasharray="4,4"/>
      <path d="${p1}" fill="none" stroke="${c1}" stroke-width="2"/>
      <path d="${p2}" fill="none" stroke="${c2}" stroke-width="2"/>
      <path d="${p3}" fill="none" stroke="${c3}" stroke-width="1.5"/>
    `;
  }

  createSvgPath(data, width, height, padding, maxVal) {
    if (data.length < 2) return "";
    const usableW = width - 2 * padding;
    const usableH = height - 2 * padding;
    const step = usableW / (data.length - 1);

    let path = "";
    data.forEach((val, idx) => {
      const clamped = Math.max(0, Math.min(maxVal, val));
      const x = padding + idx * step;
      const y = height - padding - (clamped / maxVal) * usableH;
      if (idx === 0) {
        path += `M ${x.toFixed(1)} ${y.toFixed(1)}`;
      } else {
        path += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
      }
    });
    return path;
  }

  renderAlertFeed(alerts) {
    if (!alerts || alerts.length === 0) {
      this.alertFeedEl.innerHTML = `
        <div style="padding:16px; text-align:center; color:var(--text-muted); font-family:var(--font-sans); font-size:11px;">
          ✓ NO ACTIVE HAZARD ALERTS<br/>All mesh sensors reporting within safe operational envelopes.
        </div>
      `;
      return;
    }

    let html = "";
    alerts.forEach((a) => {
      const reasonsList = (a.reasons || []).map((r) => `<li>${r}</li>`).join("");
      const isAck = a.acknowledged;

      html += `
        <div class="alert-feed-item ${a.severity}">
          <div class="alert-item-header">
            <span class="alert-item-title" style="color:${this.getSeverityColor(a.severity)}">
              [${a.severity}] ${a.title}
            </span>
            <span class="alert-item-time">${a.node_id} • Score: ${Math.round(a.score)}</span>
          </div>
          <ul class="alert-item-reasons">
            ${reasonsList}
          </ul>
          <div class="alert-item-footer">
            <span style="font-size:9px; color:var(--text-muted); font-family:var(--font-mono);">
              ID: ${a.event_id}
            </span>
            ${
              isAck
                ? `<span class="ack-badge">✓ ACK BY ${a.acknowledged_by || "OPERATOR"}</span>`
                : `<button class="ack-btn" onclick="app.ackAlert('${a.event_id}')">ACKNOWLEDGE</button>`
            }
          </div>
        </div>
      `;
    });
    this.alertFeedEl.innerHTML = html;
  }

  async ackAlert(eventId) {
    try {
      const res = await fetch("/api/alerts/ack", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event_id: eventId, acknowledged_by: sessionStorage.getItem("sih_auth_user") || "Duty Officer" })
      });
      if (res.ok) {
        this.fetchOverview();
      }
    } catch (e) {
      console.error("Ack alert error:", e);
    }
  }

  renderNodeMap(nodes) {
    const width = 350;
    const height = 125;
    this.mapSvg.setAttribute("viewBox", `0 0 ${width} ${height}`);

    const nodeCoords = {
      NODE_001: { x: 80, y: 35, label: "NODE_001 (Forest)" },
      NODE_002: { x: 190, y: 90, label: "NODE_002 (Drainage)" },
      NODE_003: { x: 280, y: 40, label: "NODE_003 (Industrial)" },
      NODE_004: { x: 120, y: 100, label: "NODE_004 (Residential)" }
    };

    let svgContent = `
      <!-- Topology Grid lines -->
      <line x1="20" y1="20" x2="330" y2="20" stroke="var(--border-subtle)" stroke-width="1"/>
      <line x1="20" y1="65" x2="330" y2="65" stroke="var(--border-subtle)" stroke-width="1"/>
      <line x1="20" y1="105" x2="330" y2="105" stroke="var(--border-subtle)" stroke-width="1"/>

      <!-- Mesh Interlink Lines -->
      <line x1="80" y1="35" x2="190" y2="90" stroke="var(--border-active)" stroke-dasharray="2,2" stroke-width="1"/>
      <line x1="190" y1="90" x2="280" y2="40" stroke="var(--border-active)" stroke-dasharray="2,2" stroke-width="1"/>
      <line x1="80" y1="35" x2="120" y2="100" stroke="var(--border-active)" stroke-dasharray="2,2" stroke-width="1"/>
    `;

    nodes.forEach((n) => {
      const pos = nodeCoords[n.node_id] || { x: 150, y: 60, label: n.node_id };
      const isSelected = n.node_id === this.selectedNodeId;
      const highestSev = n.latest_scores ? n.latest_scores.highest_severity : "NORMAL";
      const markerColor = this.getSeverityColor(highestSev);

      svgContent += `
        <g class="map-node-marker" onclick="app.selectNode('${n.node_id}')">
          ${isSelected ? `<circle cx="${pos.x}" cy="${pos.y}" r="13" fill="none" stroke="var(--border-focus)" stroke-width="1.5" stroke-dasharray="3,3"/>` : ""}
          ${highestSev === "CRITICAL" ? `<circle cx="${pos.x}" cy="${pos.y}" r="17" fill="none" stroke="var(--sev-critical-border)" stroke-width="1.5" opacity="0.7"/>` : ""}
          <circle cx="${pos.x}" cy="${pos.y}" r="6.5" fill="var(--bg-panel)" stroke="${markerColor}" stroke-width="2"/>
          <circle cx="${pos.x}" cy="${pos.y}" r="2.5" fill="${markerColor}"/>
          <text x="${pos.x}" y="${pos.y - 9}" fill="var(--text-secondary)" font-size="8.5" font-family="var(--font-sans)" font-weight="600" text-anchor="middle">${pos.label}</text>
        </g>
      `;
    });

    this.mapSvg.innerHTML = svgContent;
  }

  selectNode(nodeId) {
    this.selectedNodeId = nodeId;
    const currentData = this.latestStates[nodeId];
    if (currentData) {
      this.activeNodeNameEl.textContent = `${nodeId}`;
      this.renderHazardMatrix(currentData.scores, currentData.anomaly_stats);
      this.renderTelemetryGrid(currentData.readings, currentData.normalized, currentData.anomaly_stats);
      this.renderOledMirror(currentData.readings, currentData.scores);
      this.renderCharts(nodeId);
    }
  }

  async triggerScenario(scenario) {
    try {
      const res = await fetch("/api/simulator/scenario", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario: scenario, node_id: this.selectedNodeId })
      });
      if (res.ok) {
        this.fetchOverview();
      }
    } catch (e) {
      console.error("Trigger scenario error:", e);
    }
  }
}

// Global instance launcher
let app;
window.addEventListener("DOMContentLoaded", () => {
  app = new CommandCenterApp();
});
