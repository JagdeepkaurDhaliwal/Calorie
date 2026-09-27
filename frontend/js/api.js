// Unified API Client for CalorieCast
// Supports dynamic base URL resolution across Browser, Android Native App (WebViewAssetLoader), and Production Deployments
// Includes automatic offline / demo mode fallback and in-app server connection manager.

const API = {
  getBaseUrl() {
    // 1. Injected by Android Native WebView Bridge if running in CalorieCast APK
    if (window.AndroidBridge && typeof window.AndroidBridge.getServerAddress === "function") {
      try {
        const raw = window.AndroidBridge.getServerAddress();
        if (raw) {
          let clean = raw.trim();
          if (!clean.startsWith("http://") && !clean.startsWith("https://")) {
            clean = "http://" + clean;
          }
          const u = new URL(clean);
          return u.origin;
        }
      } catch (e) {
        console.warn("Could not read server address from AndroidBridge:", e);
      }
    }

    // 2. User configured persistence in localStorage
    const saved = localStorage.getItem("caloriecast_api_base");
    if (saved && saved.startsWith("http")) {
      return saved.replace(/\/+$/, "");
    }

    // 3. Global window configuration override (e.g. for cloud deployments or CI/CD)
    if (window.__CALORIECAST_API_BASE__) {
      return window.__CALORIECAST_API_BASE__.replace(/\/+$/, "");
    }

    // 4. Default to current browser / WebView origin IF running on real HTTP/HTTPS web host
    // (Never use origin if running inside Android asset loader domain 'androidplatform.net' or file://)
    if (
      window.location &&
      window.location.origin &&
      window.location.origin !== "null" &&
      !window.location.origin.startsWith("file:") &&
      !window.location.origin.includes("androidplatform.net") &&
      !window.location.origin.includes("appassets")
    ) {
      return window.location.origin;
    }

    // 5. Reachable Development LAN IP Fallback for local physical device testing
    return "http://172.19.217.120:8000";
  },

  get baseUrl() {
    return this.getBaseUrl();
  },

  setBaseUrl(newUrl) {
    if (!newUrl) return;
    let clean = newUrl.trim();
    if (!clean.startsWith("http://") && !clean.startsWith("https://")) {
      clean = "http://" + clean;
    }
    clean = clean.replace(/\/+$/, "");
    localStorage.setItem("caloriecast_api_base", clean);
    if (window.AndroidBridge && typeof window.AndroidBridge.setServerAddress === "function") {
      try {
        window.AndroidBridge.setServerAddress(clean);
      } catch (e) {
        console.warn("Could not update AndroidBridge server address:", e);
      }
    }
  },

  isDemoMode() {
    const token = typeof Auth !== "undefined" ? Auth.getToken() : localStorage.getItem("caloriecast_token");
    return token === "demo-offline-token-xyz" || localStorage.getItem("caloriecast_demo_mode") === "1";
  },

  async request(endpoint, options = {}) {
    // If explicitly running in demo mode, serve local mock data immediately
    if (this.isDemoMode()) {
      const mock = this.getMockResponse(endpoint, options);
      if (mock !== undefined) {
        return mock;
      }
    }

    const base = this.baseUrl;
    const url = `${base}${endpoint}`;
    const headers = options.headers || {};

    const token = typeof Auth !== "undefined" ? Auth.getToken() : localStorage.getItem("caloriecast_token");
    if (token && !headers["Authorization"] && token !== "demo-offline-token-xyz") {
      headers["Authorization"] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }

    const config = {
      ...options,
      headers,
    };

    let response;
    try {
      // Add a 5-second fetch timeout so mobile apps never hang on dead sockets
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), options.timeoutMs || 5000);
      config.signal = controller.signal;

      response = await fetch(url, config);
      clearTimeout(timeoutId);
    } catch (err) {
      // Network failure or timeout: Fallback gracefully to demo mock data if available
      console.warn(`[API] Network error connecting to ${url}: ${err.message}. Checking offline fallback...`);
      const fallbackMock = this.getMockResponse(endpoint, options);
      if (fallbackMock !== undefined) {
        this.updateConnectionPill(false, "Offline / Demo");
        return fallbackMock;
      }
      throw new Error(`Unable to connect to CalorieCast server (${url}). Please check your Wi-Fi connection or tap the server status button.`);
    }

    this.updateConnectionPill(true, "Live Server");

    if (response.status === 204) {
      return null;
    }

    let data;
    try {
      data = await response.json();
    } catch (err) {
      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }
      return null;
    }

    if (!response.ok) {
      if (response.status === 401 && typeof Auth !== "undefined") {
        Auth.clear();
        window.location.href = "/static/login.html?expired=1";
      }
      const message = data.error?.message || data.message || `Request failed with status ${response.status}`;
      const err = new Error(message);
      err.status = response.status;
      err.data = data;
      throw err;
    }

    return data;
  },

  get(endpoint) {
    return this.request(endpoint, { method: "GET" });
  },

  post(endpoint, body) {
    return this.request(endpoint, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  put(endpoint, body) {
    return this.request(endpoint, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  },

  delete(endpoint) {
    return this.request(endpoint, { method: "DELETE" });
  },

  upload(endpoint, formData) {
    return this.request(endpoint, {
      method: "POST",
      body: formData,
    });
  },

  // -------------------------------------------------------------
  // Built-in Mock / Offline Fallback Provider
  // Ensures the app UI is 100% interactive even without a backend!
  // -------------------------------------------------------------
  getMockResponse(endpoint, options) {
    const ep = endpoint.split("?")[0];

    if (ep === "/health") {
      return { status: "ok", active_model_version: 1, mode: "demo_offline" };
    }

    if (ep === "/users/me") {
      return {
        id: 1,
        email: "alex@example.com",
        name: "Alex Demo",
        role: "user",
        age: 28,
        gender: "male",
        weight_kg: 72.5,
        height_cm: 178.0,
      };
    }

    if (ep === "/workouts/body-part-summary") {
      return {
        total_exercise_calories: 520.0,
        body_parts: {
          chest: 160.0,
          legs: 210.0,
          back: 90.0,
          biceps: 60.0,
        },
        details: [
          { id: 1, body_part: "chest", exercise_name: "Incline Barbell Bench Press", calories_burnt: 160.0, duration: 30, heart_rate: 145 },
          { id: 2, body_part: "legs", exercise_name: "Barbell Back Squats", calories_burnt: 210.0, duration: 35, heart_rate: 155 },
          { id: 3, body_part: "back", exercise_name: "Lat Pulldown & Rows", calories_burnt: 90.0, duration: 20, heart_rate: 138 },
          { id: 4, body_part: "biceps", exercise_name: "Standing Dumbbell Curls", calories_burnt: 60.0, duration: 15, heart_rate: 128 },
        ],
      };
    }

    if (ep === "/workouts/summary") {
      return {
        total_calories: 2450.0,
        avg_calories: 490.0,
        workout_count: 14,
        current_week_calories: 2450.0,
      };
    }

    if (ep === "/forecast/weekly") {
      return {
        forecast_method: "Exponential Moving Average (alpha=0.5)",
        total_expected_burn: 3480.0,
        days: [
          { day: "Monday", predicted_calories: 510.0, status: "Projected" },
          { day: "Tuesday", predicted_calories: 480.0, status: "Projected" },
          { day: "Wednesday", predicted_calories: 590.0, status: "Projected" },
          { day: "Thursday", predicted_calories: 440.0, status: "Projected" },
          { day: "Friday", predicted_calories: 530.0, status: "Projected" },
          { day: "Saturday", predicted_calories: 620.0, status: "Projected" },
          { day: "Sunday", predicted_calories: 310.0, status: "Projected" },
        ],
      };
    }

    if (ep === "/workouts") {
      if (options.method === "POST") {
        return { id: Math.floor(Math.random() * 1000) + 10, message: "Workout logged in Demo Mode!" };
      }
      return {
        items: [
          { id: 101, created_at: new Date().toISOString(), duration_minutes: 45, heart_rate_avg: 148, body_temp_avg: 37.8, calories_burnt: 485.5, intensity: "Moderate", source: "Mobile App" },
          { id: 100, created_at: new Date(Date.now() - 86400000).toISOString(), duration_minutes: 35, heart_rate_avg: 156, body_temp_avg: 38.1, calories_burnt: 420.0, intensity: "High", source: "Mobile App" },
          { id: 99, created_at: new Date(Date.now() - 172800000).toISOString(), duration_minutes: 50, heart_rate_avg: 139, body_temp_avg: 37.5, calories_burnt: 510.0, intensity: "Moderate", source: "Mobile App" },
        ],
        total: 14,
        page: 1,
        page_size: 10,
        total_pages: 2,
      };
    }

    if (ep === "/predict") {
      // Local formula predictor
      let body = {};
      try { body = JSON.parse(options.body || "{}"); } catch (e) {}
      const duration = Number(body.duration_minutes || body.duration || 30);
      const hr = Number(body.heart_rate_avg || body.heart_rate || 140);
      const weight = Number(body.weight_kg || 72.5);
      const est = Math.round((duration * hr * 0.075 * (weight / 70.0)) * 10) / 10;
      return {
        calories_burnt: est,
        model_version: 1,
        confidence_interval: [Math.round(est * 0.92), Math.round(est * 1.08)],
        features_used: body,
      };
    }

    if (ep === "/ai-agent/chat" || ep === "/ai/assistant-chat") {
      return {
        reply: "Great workout consistency! In demo mode, your data shows strong chest and leg training this week. Remember to maintain hydration (3L+) and prioritize 7-8 hours of sleep for optimal muscle hypertrophy and recovery.",
        suggested_actions: ["Suggest a high-protein lunch", "Give me a 20-min HIIT workout", "How to optimize recovery?"],
        timestamp: new Date().toISOString(),
      };
    }

    if (ep === "/ai/current-plan" || ep === "/ai/general-plan" || ep === "/ai/personalized-plan") {
      return {
        id: 1,
        title: "Balanced Hypertrophy & Calorie Shred",
        summary: "Optimal 4-day split prioritizing compound movements, hypertrophy volume, and steady-state cardiovascular conditioning.",
        daily_calorie_target: 2350,
        workout_plan: {
          schedule: [
            { day: "Monday", focus: "Chest & Triceps", duration_min: 45, target_sets: "4 sets x 8-12 reps", exercises: ["Barbell Bench Press", "Incline Dumbbell Press", "Tricep Rope Pushdowns"] },
            { day: "Tuesday", focus: "Back & Biceps", duration_min: 45, target_sets: "4 sets x 10 reps", exercises: ["Lat Pulldowns", "Bent-Over Rows", "Barbell Bicep Curls"] },
            { day: "Thursday", focus: "Legs & Core", duration_min: 50, target_sets: "4 sets x 10-15 reps", exercises: ["Barbell Squats", "Romanian Deadlifts", "Plank & Leg Raises"] },
            { day: "Saturday", focus: "Full Body HIIT", duration_min: 35, target_sets: "Circuit 3 rounds", exercises: ["Kettlebell Swings", "Burpees", "Rowing Machine Sprint"] },
          ]
        },
        nutrition_plan: {
          macro_distribution: { protein_pct: 30, carbs_pct: 45, fat_pct: 25 },
          daily_protein_target_grams: 165,
          daily_carbs_target_grams: 245,
          daily_fat_target_grams: 65,
          disclaimer: "⚠ Safety Disclaimer: This plan is for informational and educational guidance. Consult a healthcare professional before starting an intensive regimen."
        }
      };
    }

    if (ep === "/nutrition/today") {
      return {
        daily_target: 2200,
        consumed_calories: 1450.0,
        exercise_calories: 520.0,
        net_calories: 930.0,
        remaining_calories: 750.0,
        status: "safe",
        status_message: "On track! 750 kcal remaining for dinner and post-workout recovery.",
        total_protein: 110.0,
        total_carbs: 145.0,
        total_fat: 45.0,
        meals: [
          { id: 1, name: "Rolled Oatmeal & Whey", calories: 380, protein: 32, carbs: 48, fat: 6, meal_type: "breakfast" },
          { id: 2, name: "Grilled Chicken Breast & Rice", calories: 520, protein: 48, carbs: 55, fat: 8, meal_type: "lunch" },
        ]
      };
    }

    if (ep === "/exercises") {
      return [
        { id: 1, name: "Bench Press", body_part: "chest", exercise_type: "strength", default_duration_min: 30, met_multiplier: 6.0 },
        { id: 2, name: "Incline Dumbbell Press", body_part: "chest", exercise_type: "strength", default_duration_min: 25, met_multiplier: 5.5 },
        { id: 3, name: "Barbell Back Squat", body_part: "legs", exercise_type: "strength", default_duration_min: 35, met_multiplier: 7.0 },
        { id: 4, name: "Treadmill Running", body_part: "legs", exercise_type: "cardio", default_duration_min: 30, met_multiplier: 9.8 },
        { id: 5, name: "Lat Pulldown", body_part: "back", exercise_type: "strength", default_duration_min: 25, met_multiplier: 5.0 },
        { id: 6, name: "Barbell Bicep Curl", body_part: "biceps", exercise_type: "strength", default_duration_min: 20, met_multiplier: 4.5 },
        { id: 7, name: "Overhead Shoulder Press", body_part: "shoulders", exercise_type: "strength", default_duration_min: 25, met_multiplier: 5.5 },
        { id: 8, name: "Tricep Pushdown", body_part: "triceps", exercise_type: "strength", default_duration_min: 20, met_multiplier: 4.5 },
        { id: 9, name: "Full Body HIIT", body_part: "full_body", exercise_type: "cardio", default_duration_min: 30, met_multiplier: 8.5 },
      ];
    }

    if (ep === "/sessions/start") {
      return { session_id: 999, message: "Live workout simulated in Demo Mode" };
    }

    if (ep.startsWith("/sessions/") && ep.endsWith("/stop")) {
      return { session_id: 999, total_calories: 385.5, duration_minutes: 25.0, avg_heart_rate: 142.0 };
    }

    if (ep === "/nutrition/foods") {
      return [
        { id: 1, name: "Rolled Oatmeal", calories: 150, protein: 5, carbs: 27, fat: 3 },
        { id: 2, name: "Whole Eggs (2)", calories: 140, protein: 12, carbs: 1, fat: 10 },
        { id: 3, name: "Grilled Chicken Breast", calories: 220, protein: 42, carbs: 0, fat: 4 },
        { id: 4, name: "Brown Rice (1 cup)", calories: 215, protein: 5, carbs: 45, fat: 2 },
        { id: 5, name: "Whey Protein Shake", calories: 120, protein: 24, carbs: 3, fat: 1 },
      ];
    }

    if (ep === "/nutrition/logs") {
      return {
        logs: [
          { id: 1, food_name: "Rolled Oatmeal & Eggs", calories: 290, protein: 17, carbs: 28, fat: 13, meal_type: "breakfast" },
          { id: 2, food_name: "Grilled Chicken & Rice", calories: 435, protein: 47, carbs: 45, fat: 6, meal_type: "lunch" },
        ],
        total_calories: 725,
        total_protein: 64,
        total_carbs: 73,
        total_fat: 19,
      };
    }

    return undefined;
  },

  // -------------------------------------------------------------
  // In-App Connection Pill & Settings Modal
  // -------------------------------------------------------------
  updateConnectionPill(isOnline, label) {
    const pill = document.getElementById("cc-server-pill");
    if (!pill) return;
    if (isOnline) {
      pill.style.background = "rgba(34, 197, 94, 0.15)";
      pill.style.borderColor = "#22c55e";
      pill.style.color = "#22c55e";
      pill.innerHTML = `🟢 ${label || "Connected"}`;
    } else {
      pill.style.background = "rgba(245, 158, 11, 0.15)";
      pill.style.borderColor = "#f59e0b";
      pill.style.color = "#f59e0b";
      pill.innerHTML = `🟡 ${label || "Offline / Demo"}`;
    }
  },

  injectServerUI() {
    if (document.getElementById("cc-server-pill")) return;

    // Create subtle top-right server status pill
    const pill = document.createElement("button");
    pill.id = "cc-server-pill";
    pill.type = "button";
    pill.style.cssText = `
      position: fixed;
      top: 10px;
      right: 12px;
      z-index: 9999;
      font-size: 11px;
      font-weight: 600;
      padding: 5px 10px;
      border-radius: 20px;
      border: 1px solid #334155;
      background: #1e293b;
      color: #94a3b8;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
      display: flex;
      align-items: center;
      gap: 5px;
      font-family: inherit;
    `;
    pill.innerHTML = `📡 Server: ${this.extractHost(this.baseUrl)}`;
    pill.onclick = () => this.openServerModal();
    document.body.appendChild(pill);

    // Initial check
    this.pingServer().then((online) => {
      this.updateConnectionPill(online, online ? "Live Server" : "Offline / Demo");
    });
  },

  extractHost(url) {
    try {
      const u = new URL(url);
      return u.host || url;
    } catch (e) {
      return url.replace(/^https?:\/\//, "").split("/")[0] || url;
    }
  },

  async pingServer(targetUrl) {
    const base = targetUrl || this.baseUrl;
    try {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), 2500);
      const res = await fetch(`${base}/health`, { signal: ctrl.signal });
      clearTimeout(t);
      return res.ok;
    } catch (e) {
      return false;
    }
  },

  openServerModal() {
    let modal = document.getElementById("cc-server-modal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "cc-server-modal";
      modal.style.cssText = `
        position: fixed;
        inset: 0;
        z-index: 10000;
        background: rgba(15, 23, 42, 0.85);
        backdrop-filter: blur(6px);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 16px;
        box-sizing: border-box;
      `;
      modal.innerHTML = `
        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 16px; max-width: 420px; width: 100%; padding: 22px; box-shadow: 0 16px 36px rgba(0,0,0,0.5); font-family: inherit; color: #f8fafc;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
            <h3 style="margin: 0; font-size: 17px; font-weight: 700; color: #38bdf8;">⚙️ Backend Server Connection</h3>
            <button id="cc-modal-close" style="background: none; border: none; color: #94a3b8; font-size: 20px; cursor: pointer; padding: 0 4px;">&times;</button>
          </div>
          
          <p style="font-size: 13px; color: #94a3b8; margin: 0 0 14px 0; line-height: 1.4;">
            Configure the CalorieCast backend address for live machine learning, authentication, and database sync.
          </p>

          <label style="font-size: 12px; font-weight: 600; color: #cbd5e1; display: block; margin-bottom: 6px;">Server Address (Host IP : Port)</label>
          <input id="cc-server-input" type="text" value="${this.baseUrl}" style="width: 100%; box-sizing: border-box; background: #0f172a; border: 1px solid #475569; border-radius: 8px; padding: 10px 12px; color: #38bdf8; font-size: 14px; margin-bottom: 12px;" />

          <div id="cc-ping-result" style="font-size: 12px; padding: 8px 12px; border-radius: 6px; margin-bottom: 14px; display: none;"></div>

          <div style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 8px;">Quick Presets:</div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 16px;">
            <button class="cc-preset-btn" data-url="http://172.19.217.120:8000" style="background: #334155; border: 1px solid #475569; color: #e2e8f0; padding: 8px; border-radius: 6px; font-size: 11px; cursor: pointer; text-align: left;">📶 Wi-Fi PC IP<br><small style="color:#94a3b8">172.19.217.120</small></button>
            <button class="cc-preset-btn" data-url="http://127.0.0.1:8000" style="background: #334155; border: 1px solid #475569; color: #e2e8f0; padding: 8px; border-radius: 6px; font-size: 11px; cursor: pointer; text-align: left;">🔌 USB Tether<br><small style="color:#94a3b8">127.0.0.1:8000</small></button>
            <button class="cc-preset-btn" data-url="http://10.0.2.2:8000" style="background: #334155; border: 1px solid #475569; color: #e2e8f0; padding: 8px; border-radius: 6px; font-size: 11px; cursor: pointer; text-align: left;">💻 Emulator<br><small style="color:#94a3b8">10.0.2.2:8000</small></button>
            <button id="cc-preset-demo" style="background: rgba(56, 189, 248, 0.15); border: 1px solid #38bdf8; color: #38bdf8; padding: 8px; border-radius: 6px; font-size: 11px; cursor: pointer; text-align: left;">🌟 Demo Mode<br><small style="color:#7dd3fc">Offline Preview</small></button>
          </div>

          <div style="display: flex; gap: 8px;">
            <button id="cc-btn-test" style="flex: 1; background: #334155; border: none; color: #f8fafc; padding: 10px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer;">🔍 Test Ping</button>
            <button id="cc-btn-save" style="flex: 1; background: #38bdf8; border: none; color: #0f172a; padding: 10px; border-radius: 8px; font-size: 13px; font-weight: 700; cursor: pointer;">💾 Save & Apply</button>
          </div>
        </div>
      `;
      document.body.appendChild(modal);

      document.getElementById("cc-modal-close").onclick = () => {
        modal.style.display = "none";
      };

      document.querySelectorAll(".cc-preset-btn").forEach((btn) => {
        btn.onclick = () => {
          document.getElementById("cc-server-input").value = btn.dataset.url;
        };
      });

      document.getElementById("cc-preset-demo").onclick = () => {
        localStorage.setItem("caloriecast_demo_mode", "1");
        if (typeof Auth !== "undefined" && !Auth.isLoggedIn()) {
          Auth.setToken("demo-offline-token-xyz");
          Auth.setUser({ id: 1, email: "alex@example.com", name: "Alex Demo", role: "user" });
        }
        alert("Demo / Offline Mode activated! The app is now fully interactive without a backend.");
        modal.style.display = "none";
        window.location.reload();
      };

      document.getElementById("cc-btn-test").onclick = async () => {
        const target = document.getElementById("cc-server-input").value.trim();
        const resBox = document.getElementById("cc-ping-result");
        resBox.style.display = "block";
        resBox.style.background = "#334155";
        resBox.style.color = "#cbd5e1";
        resBox.textContent = "Testing connection to " + target + "...";
        const ok = await API.pingServer(target);
        if (ok) {
          resBox.style.background = "rgba(34, 197, 94, 0.2)";
          resBox.style.color = "#4ade80";
          resBox.textContent = "✅ Server online and responding!";
        } else {
          resBox.style.background = "rgba(239, 68, 68, 0.2)";
          resBox.style.color = "#f87171";
          resBox.textContent = "❌ Connection failed. Check Wi-Fi or choose Demo Mode.";
        }
      };

      document.getElementById("cc-btn-save").onclick = () => {
        const target = document.getElementById("cc-server-input").value.trim();
        API.setBaseUrl(target);
        localStorage.removeItem("caloriecast_demo_mode");
        modal.style.display = "none";
        window.location.reload();
      };
    }

    modal.style.display = "flex";
    document.getElementById("cc-server-input").value = this.baseUrl;
  },
};

// Auto-inject UI helper on page load
document.addEventListener("DOMContentLoaded", () => {
  API.injectServerUI();
});
