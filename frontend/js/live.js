let activeSessionId = null;
let ws = null;
let streamTimer = null;
let clockTimer = null;
let elapsedSeconds = 0;
let simulatedHR = 110.0;
let hrMode = "moderate";
let currentLiveBodyPart = "legs";
let currentLiveExercise = "Treadmill Running";

document.addEventListener("DOMContentLoaded", () => {
  if (!Auth.requireAuth()) return;
});

function updateLiveExerciseOptions(part) {
  currentLiveBodyPart = part;
  const exInput = document.getElementById("live-exercise-name");
  const defaults = {
    chest: "Bench Press",
    back: "Lat Pulldown",
    legs: "Treadmill Running",
    shoulders: "Overhead Shoulder Press",
    biceps: "Barbell Bicep Curl",
    triceps: "Tricep Pushdown",
    full_body: "Full Body HIIT",
  };
  if (exInput) {
    exInput.value = defaults[part] || "Cardio Activity";
  }
}

async function startWorkout() {
  const bodyTempInput = document.getElementById("live-body-temp").value;
  const bodyTemp = bodyTempInput ? parseFloat(bodyTempInput) : null;
  hrMode = document.getElementById("simulation-pace").value;
  currentLiveBodyPart = document.getElementById("live-body-part").value || "legs";
  currentLiveExercise = document.getElementById("live-exercise-name").value || "Treadmill Running";

  if (hrMode === "moderate") simulatedHR = 115.0;
  else if (hrMode === "high") simulatedHR = 145.0;
  else simulatedHR = 92.0;

  try {
    const data = await API.post("/sessions/start", { body_temp: bodyTemp });
    activeSessionId = data.session_id;

    document.getElementById("pre-session-card").style.display = "none";
    document.getElementById("summary-card").style.display = "none";
    document.getElementById("active-session-card").style.display = "block";

    // Set labels
    document.getElementById("live-active-part-title").textContent = `${currentLiveBodyPart.toUpperCase()} 🔴`;
    document.getElementById("live-exercise-label").textContent = `Active: ${currentLiveExercise}`;

    // Render Body Map with Target highlighted in RED
    BodyMap.init("live-body-map-container", {
      initialPart: currentLiveBodyPart,
    });
    BodyMap.selectPart(currentLiveBodyPart);

    elapsedSeconds = 0;
    updateClock();
    clockTimer = setInterval(() => {
      elapsedSeconds++;
      updateClock();
    }, 1000);

    initStream();
  } catch (err) {
    alert("Could not start session: " + err.message);
  }
}

function updateClock() {
  const m = Math.floor(elapsedSeconds / 60).toString().padStart(2, "0");
  const s = (elapsedSeconds % 60).toString().padStart(2, "0");
  document.getElementById("live-timer").textContent = `${m}:${s}`;
}

function nextSimulatedHR() {
  let delta = (Math.random() - 0.45) * 4;
  simulatedHR += delta;
  if (hrMode === "high") simulatedHR = Math.max(125, Math.min(185, simulatedHR));
  else if (hrMode === "light") simulatedHR = Math.max(75, Math.min(115, simulatedHR));
  else simulatedHR = Math.max(100, Math.min(145, simulatedHR));
  return Math.round(simulatedHR);
}

function initStream() {
  const token = Auth.getToken();
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/sessions/${activeSessionId}/stream?token=${token}`;

  try {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      document.getElementById("live-status-mode").textContent = "CONNECTED (WS)";
      document.getElementById("live-status-mode").style.color = "var(--success)";

      streamTimer = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          const hr = nextSimulatedHR();
          document.getElementById("live-current-hr").textContent = `${hr} bpm`;
          ws.send(JSON.stringify({ type: "reading", heart_rate: hr, interval_sec: 3 }));
        }
      }, 3000);
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "update") {
        updateTelemetry(msg);
      } else if (msg.type === "summary") {
        showSummary(msg);
      } else if (msg.type === "error") {
        console.warn("WS error message:", msg.message);
      }
    };

    ws.onerror = () => {
      console.warn("WebSocket error, falling back to HTTP polling...");
      startHttpFallback();
    };

    ws.onclose = (e) => {
      if (e.code !== 1000 && activeSessionId) {
        console.warn("WebSocket closed unexpectedly:", e.code);
      }
    };
  } catch (err) {
    console.warn("Failed to create WebSocket, falling back to HTTP:", err);
    startHttpFallback();
  }
}

function startHttpFallback() {
  if (ws) {
    try { ws.close(); } catch (_) {}
    ws = null;
  }
  clearInterval(streamTimer);
  document.getElementById("live-status-mode").textContent = "POLLING (HTTP)";
  document.getElementById("live-status-mode").style.color = "var(--warning)";

  streamTimer = setInterval(async () => {
    if (!activeSessionId) return;
    const hr = nextSimulatedHR();
    document.getElementById("live-current-hr").textContent = `${hr} bpm`;
    try {
      const update = await API.post(`/sessions/${activeSessionId}/readings`, {
        heart_rate: hr,
        interval_sec: 3
      });
      updateTelemetry(update);
    } catch (err) {
      console.error("HTTP reading push failed:", err);
    }
  }, 3000);
}

function updateTelemetry(data) {
  document.getElementById("live-calories").innerHTML = `${data.cumulative_calories.toFixed(2)} <span style="font-size: 1.5rem; color: var(--text-muted);">kcal</span>`;
  document.getElementById("live-avg-hr").textContent = `${data.avg_hr.toFixed(1)} bpm`;

  const badge = document.getElementById("live-intensity-badge");
  badge.textContent = data.intensity_so_far.toUpperCase();
  badge.className = `badge badge-${data.intensity_so_far.toLowerCase()}`;
}

async function endWorkout() {
  clearInterval(clockTimer);
  clearInterval(streamTimer);

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "end" }));
  } else {
    try {
      const summary = await API.post(`/sessions/${activeSessionId}/end`);
      showSummary(summary);
    } catch (err) {
      alert("Failed to end session: " + err.message);
    }
  }
}

async function showSummary(data) {
  if (ws) {
    try { ws.close(); } catch (_) {}
    ws = null;
  }
  activeSessionId = null;

  document.getElementById("active-session-card").style.display = "none";
  document.getElementById("summary-card").style.display = "block";

  document.getElementById("sum-total-cal").textContent = `${data.total_calories.toFixed(1)} kcal`;
  document.getElementById("sum-duration").textContent = `${data.duration_min.toFixed(1)} min`;
  document.getElementById("sum-avg-hr").textContent = `${data.avg_hr.toFixed(0)} bpm`;

  // Log to workout exercises to sync with Body Calorie Map
  try {
    await API.post("/exercises/workout", {
      exercise_name: currentLiveExercise,
      exercise_type: "cardio",
      body_part: currentLiveBodyPart,
      duration_min: data.duration_min,
      heart_rate: data.avg_hr,
      intensity: data.intensity.toLowerCase(),
      notes: `Logged via Live Telemetry Session (${data.intensity})`,
    });
    document.getElementById("summary-msg").innerHTML = `
      🎉 Burned <strong>${data.total_calories.toFixed(1)} kcal</strong> for <strong>${currentLiveBodyPart.toUpperCase()} 🔴</strong>!<br>
      Saved to your workout history and Today's Body Calorie Map.
    `;
  } catch (err) {
    console.warn("Could not sync live session to exercise table:", err);
  }
}

function resetLiveUI() {
  document.getElementById("summary-card").style.display = "none";
  document.getElementById("pre-session-card").style.display = "block";
  document.getElementById("live-calories").innerHTML = `0.00 <span style="font-size: 1.5rem; color: var(--text-muted);">kcal</span>`;
  document.getElementById("live-current-hr").textContent = "-- bpm";
  document.getElementById("live-avg-hr").textContent = "-- bpm";
  document.getElementById("live-timer").textContent = "00:00";
}
