let currentPage = 1;
const pageSize = 10;
let totalPages = 1;
let bodyMapSummaryData = null;

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const BODY_PART_DESCRIPTIONS = {
  chest: "Pectorals, upper & lower chest",
  back: "Lats, rhomboids, traps, lower back",
  legs: "Quadriceps, hamstrings, glutes, calves",
  biceps: "Front upper arms, brachialis",
  triceps: "Back upper arms, long & lateral heads",
  shoulders: "Anterior, lateral, posterior deltoids",
  full_body: "Compound, athletic, whole body",
};

document.addEventListener("DOMContentLoaded", () => {
  if (!Auth.requireAuth()) return;
  Promise.allSettled([
    loadBodyCalorieMap(),
    loadSummary(),
    loadForecast(),
    loadWorkouts(currentPage)
  ]).then(results => {
    results.forEach((res, i) => {
      if (res.status === "rejected") {
        console.warn(`Dashboard component ${i} failed:`, res.reason);
      }
    });
  });
});

async function loadBodyCalorieMap() {
  try {
    const data = await API.get("/workouts/body-part-summary");
    bodyMapSummaryData = data;

    const totalEl = document.getElementById("total-today-exercise-cals");
    if (totalEl) {
      totalEl.textContent = `${data.total_exercise_calories.toFixed(1)} kcal`;
    }

    BodyMap.init("body-map-container", {
      initialPart: "chest",
      calorieData: data.body_parts,
      onSelect: (partId) => updateDetailPanel(partId),
    });

    updateDetailPanel("chest");
  } catch (err) {
    console.warn("Could not load remote body calorie map; initializing with defaults:", err.message);
    bodyMapSummaryData = {
      total_exercise_calories: 0.0,
      body_parts: {},
      details: []
    };
    BodyMap.init("body-map-container", {
      initialPart: "chest",
      calorieData: {},
      onSelect: (partId) => updateDetailPanel(partId),
    });
    updateDetailPanel("chest");
  }
}

function updateDetailPanel(partId) {
  const titleEl = document.getElementById("detail-part-title");
  const descEl = document.getElementById("detail-part-desc");
  const calsEl = document.getElementById("detail-part-cals");
  const exContainer = document.getElementById("detail-part-exercises");
  const logBtn = document.getElementById("btn-log-muscle-workout");

  if (!titleEl || !bodyMapSummaryData) return;

  const names = {
    chest: "CHEST 🔴",
    back: "BACK 🔴",
    legs: "LEGS 🔴",
    biceps: "BICEPS 🔴",
    triceps: "TRICEPS 🔴",
    shoulders: "SHOULDERS 🔴",
    full_body: "FULL BODY 🔴",
  };

  titleEl.textContent = names[partId] || `${partId.toUpperCase()} 🔴`;
  descEl.textContent = BODY_PART_DESCRIPTIONS[partId] || "Target muscle group";

  const kcal = bodyMapSummaryData.body_parts[partId] || 0.0;
  calsEl.textContent = `${kcal.toFixed(1)} kcal`;

  if (logBtn) {
    logBtn.href = `/static/workouts.html?part=${partId}`;
    logBtn.textContent = `+ Log ${partId.replace('_', ' ').toUpperCase()} Workout`;
  }

  // Find exercise details for this part
  const detail = (bodyMapSummaryData.details || []).find(d => d.body_part === partId);
  if (!detail || !detail.exercises || detail.exercises.length === 0) {
    exContainer.innerHTML = `
      <div style="color: var(--text-muted); font-size: 0.85rem; font-style: italic; padding: 0.5rem 0;">
        No ${partId} exercises logged today.
      </div>
    `;
    return;
  }

  exContainer.innerHTML = `
    <div style="font-size: 0.85rem; font-weight: 600; color: var(--text-muted); margin-bottom: 0.4rem;">
      Exercises Today (${detail.exercises.length}):
    </div>
    <div style="display: flex; flex-direction: column; gap: 0.4rem; max-height: 200px; overflow-y: auto;">
      ${detail.exercises.map(ex => `
        <div style="background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 6px; padding: 0.5rem 0.8rem; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong style="color: var(--text-main); font-size: 0.9rem;">${ex.exercise_name}</strong>
            <div style="font-size: 0.75rem; color: var(--text-muted);">
              ${ex.sets ? `${ex.sets} sets × ${ex.reps} reps @ ${ex.weight_kg || 0}kg` : `${ex.duration_min} min`}
            </div>
          </div>
          <span style="font-weight: 700; color: #ef4444; font-size: 0.9rem;">
            +${ex.calories_burned.toFixed(1)} kcal
          </span>
        </div>
      `).join('')}
    </div>
  `;
}

async function loadSummary() {
  try {
    const data = await API.get("/workouts/summary");
    document.getElementById("stat-week-total").textContent = `${data.week_total.toFixed(1)} kcal`;
    document.getElementById("stat-avg-workout").textContent = `${data.avg_per_workout.toFixed(1)} kcal`;
    document.getElementById("stat-count").textContent = data.count;
  } catch (err) {
    console.error("Error loading summary:", err);
  }
}

async function loadForecast() {
  try {
    const data = await API.get("/forecast/weekly");
    document.getElementById("forecast-total").textContent = `${data.weekly_total.toFixed(1)} kcal`;

    const badge = document.getElementById("forecast-method-badge");
    badge.textContent = `Model: ${data.method.toUpperCase()}`;
    badge.className = `badge ${data.method === "history" ? "badge-low" : "badge-seed"}`;

    const grid = document.getElementById("forecast-days-grid");
    grid.innerHTML = "";

    data.daily.forEach((kcal, idx) => {
      const card = document.createElement("div");
      card.className = "card stat-card";
      card.style.padding = "0.8rem";
      card.innerHTML = `
        <div class="stat-label" style="font-size: 0.75rem;">${DAYS[idx]}</div>
        <div style="font-size: 1.3rem; font-weight: 700; color: var(--accent); margin: 0.2rem 0;">${kcal.toFixed(1)}</div>
        <small style="color: var(--text-muted); font-size: 0.7rem;">kcal</small>
      `;
      grid.appendChild(card);
    });
  } catch (err) {
    console.error("Error loading forecast:", err);
  }
}

async function loadWorkouts(page) {
  try {
    const data = await API.get(`/workouts?page=${page}&page_size=${pageSize}`);
    currentPage = data.page;
    totalPages = Math.max(1, Math.ceil(data.total / pageSize));

    document.getElementById("page-info").textContent = `Page ${currentPage} of ${totalPages} (${data.total} total)`;
    document.getElementById("btn-prev-page").disabled = currentPage <= 1;
    document.getElementById("btn-next-page").disabled = currentPage >= totalPages;

    const tbody = document.getElementById("history-tbody");
    tbody.innerHTML = "";

    if (!data.items || data.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted);">No workouts recorded yet.</td></tr>`;
      return;
    }

    data.items.forEach(w => {
      const tr = document.createElement("tr");
      const dt = new Date(w.created_at).toLocaleString();

      tr.innerHTML = `
        <td>${dt}</td>
        <td>${w.duration_min} min</td>
        <td>${w.heart_rate.toFixed(0)} bpm</td>
        <td>${w.body_temp.toFixed(1)} °C</td>
        <td><strong>${w.predicted_calories.toFixed(1)} kcal</strong></td>
        <td><span class="badge badge-${w.intensity.toLowerCase()}">${w.intensity}</span></td>
        <td>
          <span class="badge ${w.source === 'seed' ? 'badge-seed' : 'badge-low'}">
            ${w.source}
          </span>
          ${w.extrapolated ? '<span title="Extrapolated" style="cursor:help;">⚠️</span>' : ''}
        </td>
        <td>
          <button class="btn btn-danger btn-sm" onclick="handleDelete(${w.id})">Delete</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading workouts:", err);
  }
}

function changePage(delta) {
  const target = currentPage + delta;
  if (target >= 1 && target <= totalPages) {
    loadWorkouts(target);
  }
}

async function handleDelete(id) {
  if (!confirm("Are you sure you want to delete this workout record?")) return;
  try {
    await API.delete(`/workouts/${id}`);
    loadWorkouts(currentPage);
    loadSummary();
    loadForecast();
    loadBodyCalorieMap();
  } catch (err) {
    alert(`Failed to delete workout: ${err.message}`);
  }
}
