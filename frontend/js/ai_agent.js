// AI Fitness Agent & Workout Plans

document.addEventListener("DOMContentLoaded", async () => {
  if (!Auth.requireAuth()) return;
  await loadCurrentPlan();
});

async function loadCurrentPlan() {
  try {
    const plan = await API.get("/ai/current-plan");
    if (plan) {
      renderPlan(plan);
    }
  } catch (err) {
    console.error("Error loading current plan:", err);
  }
}

async function generateMode1Plan() {
  const alertContainer = document.getElementById("alert-container");
  alertContainer.innerHTML = `<div class="alert alert-warning">⏳ Generating 7-day general fitness blueprint...</div>`;

  try {
    const plan = await API.post("/ai/general-plan");
    renderPlan(plan);
    alertContainer.innerHTML = `<div class="alert alert-success">🎉 General Fitness Plan generated successfully!</div>`;
    document.getElementById("plan-display-card").scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    alertContainer.innerHTML = `<div class="alert alert-danger">Failed to generate plan: ${err.message}</div>`;
  }
}

async function generateMode2Plan(event) {
  event.preventDefault();
  const alertContainer = document.getElementById("alert-container");
  alertContainer.innerHTML = `<div class="alert alert-warning">⏳ Calculating BMR, TDEE, and building custom blueprint...</div>`;

  const goal = document.getElementById("plan-goal").value;
  const diet = document.getElementById("plan-diet").value;
  const days = parseInt(document.getElementById("plan-days").value) || 4;

  const targetMuscles = [];
  document.querySelectorAll('input[name="target-muscle"]:checked').forEach(cb => {
    targetMuscles.push(cb.value);
  });

  const payload = {
    goal: goal,
    preferred_body_parts: targetMuscles.length > 0 ? targetMuscles : ["chest", "back", "legs"],
    dietary_preference: diet,
    workout_days_per_week: days,
  };

  try {
    const plan = await API.post("/ai/personalized-plan", payload);
    renderPlan(plan);
    alertContainer.innerHTML = `<div class="alert alert-success">🎉 Personalized Plan generated for ${goal.replace('_', ' ').toUpperCase()}!</div>`;
    document.getElementById("plan-display-card").scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    alertContainer.innerHTML = `<div class="alert alert-danger">Failed to generate plan: ${err.message}</div>`;
  }
}

function renderPlan(plan) {
  const card = document.getElementById("plan-display-card");
  card.style.display = "block";

  document.getElementById("plan-display-title").textContent = plan.title;
  document.getElementById("plan-display-summary").textContent = plan.summary;
  document.getElementById("plan-display-target").textContent = `${plan.daily_calorie_target.toFixed(0)} kcal`;

  // Render Schedule
  const scheduleGrid = document.getElementById("plan-display-schedule");
  scheduleGrid.innerHTML = "";

  const schedule = plan.workout_plan.schedule || [];
  schedule.forEach(day => {
    const dayCard = document.createElement("div");
    dayCard.className = "card stat-card";
    dayCard.style.padding = "0.9rem";
    dayCard.style.textAlign = "left";
    dayCard.style.background = "var(--bg-primary)";

    const exList = day.exercises ? day.exercises.map(e => `<li>${e}</li>`).join('') :
                   (day.notes ? `<li>${day.notes}</li>` : '');

    dayCard.innerHTML = `
      <div style="font-weight: 700; color: var(--accent); font-size: 0.95rem; border-bottom: 1px solid var(--border); padding-bottom: 0.3rem; margin-bottom: 0.5rem;">
        ${day.day}: ${day.focus}
      </div>
      <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.4rem;">
        ⏱ ${day.duration_min} min ${day.target_sets ? `• ${day.target_sets}` : ''}
      </div>
      <ul style="font-size: 0.8rem; padding-left: 1.2rem; color: var(--text-main); margin: 0;">
        ${exList}
      </ul>
    `;
    scheduleGrid.appendChild(dayCard);
  });

  // Render Nutrition Protocol
  const nutContainer = document.getElementById("plan-display-nutrition");
  const nut = plan.nutrition_plan;
  const macros = nut.macro_distribution || { protein_pct: 30, carbs_pct: 45, fat_pct: 25 };

  nutContainer.innerHTML = `
    <div class="grid grid-cols-3" style="gap: 0.8rem; margin-bottom: 1rem;">
      <div class="macro-pill" style="border-left: 3px solid #38bdf8;">
        <span class="stat-label">Protein Target</span>
        <span class="macro-val">${nut.daily_protein_target_grams ? `${nut.daily_protein_target_grams}g` : `${macros.protein_pct}%`}</span>
      </div>
      <div class="macro-pill" style="border-left: 3px solid #f59e0b;">
        <span class="stat-label">Carbs Target</span>
        <span class="macro-val">${nut.daily_carbs_target_grams ? `${nut.daily_carbs_target_grams}g` : `${macros.carbs_pct}%`}</span>
      </div>
      <div class="macro-pill" style="border-left: 3px solid #10b981;">
        <span class="stat-label">Fat Target</span>
        <span class="macro-val">${nut.daily_fat_target_grams ? `${nut.daily_fat_target_grams}g` : `${macros.fat_pct}%`}</span>
      </div>
    </div>
  `;

  // Render Safety Disclaimer
  const disclaimerEl = document.getElementById("plan-display-disclaimer");
  disclaimerEl.textContent = nut.disclaimer || "⚠ Safety Disclaimer: This plan is for informational and educational fitness guidance only. Consult a healthcare professional before starting any intensive fitness regimen.";
}

// --- AI Chat Assistant ---
async function handleSendChat(event) {
  event.preventDefault();
  const input = document.getElementById("chat-input");
  const msg = input.value.trim();
  if (!msg) return;

  appendChatBubble(msg, "user");
  input.value = "";

  try {
    const res = await API.post("/ai/assistant-chat", { message: msg });
    appendChatBubble(res.reply, "agent");

    // Update quick actions if returned
    if (res.suggested_actions && res.suggested_actions.length > 0) {
      renderChatActionChips(res.suggested_actions);
    }
  } catch (err) {
    appendChatBubble(`Error: ${err.message}`, "agent");
  }
}

function sendQuickPrompt(promptText) {
  document.getElementById("chat-input").value = promptText;
  document.querySelector(".chat-input-bar button[type='submit']").click();
}

function appendChatBubble(text, sender) {
  const container = document.getElementById("chat-messages");
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble chat-bubble-${sender}`;
  // Simple markdown formatting for bold and bullets
  const formatted = text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n\n/g, '<br><br>')
    .replace(/\n/g, '<br>');
  bubble.innerHTML = formatted;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

function renderChatActionChips(actions) {
  const container = document.getElementById("chat-quick-actions");
  if (!container) return;
  container.innerHTML = actions.map(act => `
    <button type="button" class="btn btn-secondary btn-sm" onclick="sendQuickPrompt('${act}')">
      👉 ${act}
    </button>
  `).join('');
}
