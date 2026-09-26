// Workouts & Custom Exercise Management
let currentType = "strength";
let currentPart = "chest";
let allExercises = [];

document.addEventListener("DOMContentLoaded", async () => {
  if (!Auth.requireAuth()) return;

  // Check URL query param for pre-selected body part
  const urlParams = new URLSearchParams(window.location.search);
  const requestedPart = urlParams.get("part");
  if (requestedPart) {
    currentPart = requestedPart.toLowerCase();
    const dropdown = document.getElementById("input-body-part");
    if (dropdown) dropdown.value = currentPart;
  }

  await loadBodyMapAndCalories();
  await loadExerciseLibrary();
  await loadRecentHistory();
});

async function loadBodyMapAndCalories() {
  try {
    const summary = await API.get("/workouts/body-part-summary");
    BodyMap.init("body-map-container", {
      initialPart: currentPart,
      calorieData: summary.body_parts,
      onSelect: (partId) => {
        currentPart = partId;
        const dropdown = document.getElementById("input-body-part");
        if (dropdown) dropdown.value = partId;
        populateExerciseDropdown();
      }
    });
  } catch (err) {
    console.error("Error loading body calorie map:", err);
  }
}

async function loadExerciseLibrary() {
  try {
    allExercises = await API.get("/exercises");
    populateExerciseDropdown();
  } catch (err) {
    console.error("Error loading exercises:", err);
  }
}

function onBodyPartDropdownChange(newPart) {
  currentPart = newPart;
  BodyMap.selectPart(newPart);
  populateExerciseDropdown();
}

function setExerciseType(type) {
  currentType = type;

  // Update tabs
  ["strength", "cardio", "recovery"].forEach(t => {
    const btn = document.getElementById(`tab-btn-${t}`);
    if (btn) {
      btn.className = (t === type) ? "btn btn-primary" : "btn btn-secondary";
    }
  });

  // Toggle sections
  document.getElementById("section-strength").style.display = (type === "strength") ? "block" : "none";
  document.getElementById("section-cardio").style.display = (type === "cardio") ? "block" : "none";
  document.getElementById("section-recovery").style.display = (type === "recovery") ? "block" : "none";

  // Hide body part selector for cardio / recovery if not strictly muscle-focused
  const bpGroup = document.getElementById("group-body-part");
  if (bpGroup) {
    bpGroup.style.display = (type === "strength") ? "block" : "none";
  }

  populateExerciseDropdown();
}

function populateExerciseDropdown() {
  const select = document.getElementById("input-exercise-select");
  if (!select) return;
  select.innerHTML = "";

  let filtered = [];
  if (currentType === "strength") {
    filtered = allExercises.filter(e => e.category === "strength" && e.body_part === currentPart);
    if (filtered.length === 0) {
      filtered = allExercises.filter(e => e.category === "strength");
    }
  } else if (currentType === "cardio") {
    filtered = allExercises.filter(e => e.category === "cardio");
  } else if (currentType === "recovery") {
    filtered = allExercises.filter(e => e.category === "recovery");
  }

  filtered.forEach(ex => {
    const opt = document.createElement("option");
    opt.value = ex.id;
    opt.dataset.name = ex.name;
    opt.dataset.bodyPart = ex.body_part;
    opt.textContent = `${ex.name} (${ex.category.toUpperCase()})`;
    select.appendChild(opt);
  });

  // Custom option
  const customOpt = document.createElement("option");
  customOpt.value = "custom";
  customOpt.textContent = "+ Custom Exercise...";
  select.appendChild(customOpt);
}

function onExerciseSelectChange() {
  const select = document.getElementById("input-exercise-select");
  if (select.value === "custom") {
    const customName = prompt("Enter custom exercise name:");
    if (customName && customName.trim()) {
      const opt = document.createElement("option");
      opt.value = "custom_" + Date.now();
      opt.dataset.name = customName.trim();
      opt.textContent = `★ ${customName.trim()} (Custom)`;
      opt.selected = true;
      select.insertBefore(opt, select.firstChild);
    }
  }
}

async function handleLogWorkout(event) {
  event.preventDefault();
  const alertContainer = document.getElementById("alert-container");
  alertContainer.innerHTML = "";

  const select = document.getElementById("input-exercise-select");
  const selectedOpt = select.options[select.selectedIndex];
  const exName = selectedOpt ? (selectedOpt.dataset.name || selectedOpt.textContent) : "Exercise";
  const exId = (select.value && !select.value.startsWith("custom")) ? parseInt(select.value) : null;

  const payload = {
    exercise_id: exId,
    exercise_name: exName,
    exercise_type: currentType,
    body_part: (currentType === "strength") ? currentPart : (selectedOpt?.dataset?.bodyPart || "legs"),
    intensity: document.getElementById("input-intensity").value,
    notes: document.getElementById("input-notes").value || null,
  };

  if (currentType === "strength") {
    payload.sets = parseInt(document.getElementById("input-sets").value) || 4;
    payload.reps = parseInt(document.getElementById("input-reps").value) || 10;
    payload.weight_kg = parseFloat(document.getElementById("input-weight").value) || 0.0;
    payload.duration_min = parseFloat(document.getElementById("input-strength-duration").value) || 30.0;
    payload.rest_time_sec = parseInt(document.getElementById("input-rest").value) || 60;
  } else if (currentType === "cardio") {
    payload.duration_min = parseFloat(document.getElementById("input-cardio-duration").value) || 30.0;
    const hr = document.getElementById("input-cardio-hr").value;
    if (hr) payload.heart_rate = parseFloat(hr);
    const dist = document.getElementById("input-distance").value;
    if (dist) payload.distance_km = parseFloat(dist);
  } else if (currentType === "recovery") {
    payload.duration_min = 20.0;
  }

  try {
    const res = await API.post("/exercises/workout", payload);

    alertContainer.innerHTML = `
      <div class="alert alert-success">
        🎉 Successfully logged <strong>${res.exercise_name}</strong>! Burned <strong>${res.calories_burned.toFixed(1)} kcal</strong> on <strong>${res.body_part.toUpperCase()} 🔴</strong>.
      </div>
    `;

    // Refresh body calorie map and history
    await loadBodyMapAndCalories();
    await loadRecentHistory();

    // Reset notes
    document.getElementById("input-notes").value = "";
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (err) {
    alertContainer.innerHTML = `
      <div class="alert alert-danger">
        Failed to log workout: ${err.message}
      </div>
    `;
  }
}

async function loadRecentHistory() {
  const container = document.getElementById("recent-exercises-list");
  if (!container) return;

  try {
    const list = await API.get("/exercises/history?limit=10");
    if (!list || list.length === 0) {
      container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.9rem;">No workouts recorded yet. Use the form above to log your first exercise!</div>`;
      return;
    }

    container.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 0.6rem;">
        ${list.map(w => {
          const dt = new Date(w.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          return `
            <div style="background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; padding: 0.8rem 1rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
              <div>
                <strong style="color: var(--text-main); font-size: 1rem;">${w.exercise_name}</strong>
                <span class="badge" style="background: rgba(239,68,68,0.2); color: #fca5a5; margin-left: 0.5rem; font-size: 0.75rem;">
                  ${w.body_part.toUpperCase()} 🔴
                </span>
                <span class="badge badge-${w.intensity}" style="margin-left: 0.3rem;">${w.intensity}</span>
                <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.2rem;">
                  ${w.sets ? `${w.sets} sets × ${w.reps} reps (${w.weight_kg || 0}kg) • ` : ''}${w.duration_min} min • ${dt}
                </div>
              </div>
              <div style="text-align: right;">
                <div style="font-size: 1.3rem; font-weight: 700; color: #ef4444;">
                  +${w.calories_burned.toFixed(1)} kcal
                </div>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  } catch (err) {
    console.error("Error loading recent history:", err);
  }
}
