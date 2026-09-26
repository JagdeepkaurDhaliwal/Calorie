// Nutrition & AI Food Calorie Image Analysis
let foodCatalogue = [];
let currentModalMealType = "breakfast";
let currentAnalysisId = null;
let currentDetectedItems = [];

document.addEventListener("DOMContentLoaded", async () => {
  if (!Auth.requireAuth()) return;
  await loadDailyNutrition();
  await loadFoodCatalogue();
  await loadRecommendations();
});

async function loadDailyNutrition() {
  try {
    const summary = await API.get("/nutrition/today");
    renderNutritionSummary(summary);
  } catch (err) {
    console.error("Error loading daily nutrition:", err);
  }
}

function renderNutritionSummary(summary) {
  document.getElementById("val-target-cals").textContent = `${summary.daily_target.toFixed(0)} kcal`;
  document.getElementById("val-consumed-cals").textContent = `${summary.consumed_calories.toFixed(1)} kcal`;
  document.getElementById("val-exercise-cals").textContent = `-${summary.exercise_calories.toFixed(1)} kcal`;
  document.getElementById("val-net-cals").textContent = `${summary.net_calories.toFixed(1)} kcal`;

  const remainingEl = document.getElementById("val-remaining-cals");
  remainingEl.textContent = `${summary.remaining_calories.toFixed(0)} kcal`;
  if (summary.remaining_calories < 0) {
    remainingEl.style.color = "#ef4444";
  } else {
    remainingEl.style.color = "var(--accent)";
  }

  // Progress Bar
  const pct = Math.min(Math.max((summary.consumed_calories / summary.daily_target) * 100, 0), 100);
  const fillBar = document.getElementById("calorie-progress-fill");
  fillBar.style.width = `${pct}%`;
  fillBar.className = "progress-bar-fill " + (
    summary.status === "over_target" ? "fill-danger" :
    summary.status === "approaching_target" ? "fill-warn" : "fill-safe"
  );

  // Status message
  const statusMsg = document.getElementById("status-message");
  statusMsg.textContent = summary.status_message;
  if (summary.status === "over_target") {
    statusMsg.style.color = "#f87171";
  } else if (summary.status === "approaching_target") {
    statusMsg.style.color = "#fcd34d";
  } else {
    statusMsg.style.color = "var(--text-muted)";
  }

  // Macros
  document.getElementById("val-total-protein").textContent = `${summary.total_protein.toFixed(1)} g`;
  document.getElementById("val-total-carbs").textContent = `${summary.total_carbs.toFixed(1)} g`;
  document.getElementById("val-total-fat").textContent = `${summary.total_fat.toFixed(1)} g`;

  // Render Meal Cards
  ["breakfast", "lunch", "dinner", "snack"].forEach(type => {
    const meal = summary.meals[type];
    const calsEl = document.getElementById(`cals-meal-${type}`);
    const itemsEl = document.getElementById(`items-meal-${type}`);

    if (meal && meal.items && meal.items.length > 0) {
      calsEl.textContent = `${meal.total_calories.toFixed(1)} kcal`;
      itemsEl.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 0.4rem;">
          ${meal.items.map(item => `
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.3rem;">
              <div>
                <strong style="color: var(--text-main); font-size: 0.88rem;">${item.food_name}</strong>
                <div style="font-size: 0.75rem; color: var(--text-muted);">${item.quantity} ${item.is_ai_detected ? '• <span style="color:var(--accent);">🤖 AI</span>' : ''}</div>
              </div>
              <div style="text-align: right; font-size: 0.85rem; font-weight: 600; color: var(--text-main);">
                ${item.calories.toFixed(0)} kcal
              </div>
            </div>
          `).join('')}
        </div>
      `;
    } else {
      calsEl.textContent = `0.0 kcal`;
      itemsEl.innerHTML = `<div style="font-size: 0.85rem; color: var(--text-muted); font-style: italic;">No items logged yet.</div>`;
    }
  });
}

// --- AI Food Calorie Image Analysis ---
function previewFoodImage(event) {
  const file = event.target.files[0];
  const preview = document.getElementById("food-image-preview");
  const placeholder = document.getElementById("preview-placeholder");
  const btn = document.getElementById("btn-analyze-food");

  if (file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      preview.src = e.target.result;
      preview.style.display = "block";
      placeholder.style.display = "none";
      btn.disabled = false;
    };
    reader.readAsDataURL(file);
  } else {
    preview.style.display = "none";
    placeholder.style.display = "block";
    btn.disabled = true;
  }
}

async function analyzeFoodImage() {
  const fileInput = document.getElementById("food-image-input");
  const file = fileInput.files[0];
  if (!file) return;

  const btn = document.getElementById("btn-analyze-food");
  btn.disabled = true;
  btn.textContent = "⏳ Analyzing with AI vision...";

  try {
    const formData = new FormData();
    formData.append("file", file);

    const result = await API.upload("/food/analyze-image", formData);
    currentAnalysisId = result.analysis_id;
    currentDetectedItems = result.detected_items;

    // Show Results
    const resultsContainer = document.getElementById("ai-analysis-results");
    resultsContainer.style.display = "block";
    document.getElementById("ai-detected-total-badge").textContent = `Total: ~${result.total_calories.toFixed(0)} kcal`;
    document.getElementById("ai-confirm-meal-type").value = result.suggested_meal || "lunch";

    renderDetectedItemsTable(result.detected_items);
    resultsContainer.scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    alert(`AI analysis failed: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = "✨ Run AI Vision Analysis";
  }
}

function renderDetectedItemsTable(items) {
  const container = document.getElementById("ai-detected-items-table");
  container.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Detected Food</th>
          <th>Portion</th>
          <th>Calories</th>
          <th>Protein (g)</th>
          <th>Carbs (g)</th>
          <th>Fat (g)</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        ${items.map((item, idx) => `
          <tr>
            <td><input type="text" id="ai-item-name-${idx}" value="${item.name}" style="padding: 0.3rem; font-size: 0.85rem; width: 100%;"></td>
            <td><input type="text" id="ai-item-portion-${idx}" value="${item.portion}" style="padding: 0.3rem; font-size: 0.85rem; width: 100px;"></td>
            <td><input type="number" id="ai-item-cals-${idx}" value="${item.calories}" style="padding: 0.3rem; font-size: 0.85rem; width: 75px;"></td>
            <td><input type="number" step="0.1" id="ai-item-p-${idx}" value="${item.protein}" style="padding: 0.3rem; font-size: 0.85rem; width: 60px;"></td>
            <td><input type="number" step="0.1" id="ai-item-c-${idx}" value="${item.carbs}" style="padding: 0.3rem; font-size: 0.85rem; width: 60px;"></td>
            <td><input type="number" step="0.1" id="ai-item-f-${idx}" value="${item.fat}" style="padding: 0.3rem; font-size: 0.85rem; width: 60px;"></td>
            <td><button type="button" class="btn btn-danger btn-sm" onclick="removeAiItemRow(${idx})">✕</button></td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

function removeAiItemRow(idx) {
  currentDetectedItems.splice(idx, 1);
  renderDetectedItemsTable(currentDetectedItems);
}

async function confirmAiFoodAnalysis() {
  const mealType = document.getElementById("ai-confirm-meal-type").value;
  const items = [];

  for (let i = 0; i < currentDetectedItems.length; i++) {
    const nameEl = document.getElementById(`ai-item-name-${i}`);
    if (!nameEl) continue;
    items.push({
      food_name: nameEl.value,
      quantity: document.getElementById(`ai-item-portion-${i}`).value,
      calories: parseFloat(document.getElementById(`ai-item-cals-${i}`).value) || 0.0,
      protein: parseFloat(document.getElementById(`ai-item-p-${i}`).value) || 0.0,
      carbs: parseFloat(document.getElementById(`ai-item-c-${i}`).value) || 0.0,
      fat: parseFloat(document.getElementById(`ai-item-f-${i}`).value) || 0.0,
    });
  }

  if (items.length === 0) {
    alert("No items to confirm!");
    return;
  }

  const payload = {
    analysis_id: currentAnalysisId,
    meal_type: mealType,
    items: items,
  };

  try {
    await API.post("/food/confirm", payload);
    document.getElementById("alert-container").innerHTML = `
      <div class="alert alert-success">
        🎉 Confirmed and logged ${items.length} items to ${mealType.toUpperCase()}!
      </div>
    `;

    document.getElementById("ai-analysis-results").style.display = "none";
    document.getElementById("food-image-input").value = "";
    document.getElementById("food-image-preview").style.display = "none";
    document.getElementById("preview-placeholder").style.display = "block";
    document.getElementById("btn-analyze-food").disabled = true;

    await loadDailyNutrition();
    await loadRecommendations();
  } catch (err) {
    alert(`Failed to confirm meal: ${err.message}`);
  }
}

// --- Food Item Catalogue & Manual Modal ---
async function loadFoodCatalogue() {
  try {
    foodCatalogue = await API.get("/nutrition/food-items");
  } catch (err) {
    console.error("Error loading catalogue:", err);
  }
}

function openAddFoodModal(mealType) {
  currentModalMealType = mealType;
  document.getElementById("modal-meal-title").textContent = `Add to ${mealType.toUpperCase()}`;

  const select = document.getElementById("modal-food-select");
  select.innerHTML = `<option value="">-- Choose from Staple Foods (or enter below) --</option>`;
  foodCatalogue.forEach((f, idx) => {
    const opt = document.createElement("option");
    opt.value = idx;
    opt.textContent = `${f.name} (${f.serving_size} - ${f.calories} kcal)`;
    select.appendChild(opt);
  });

  // Clear inputs
  document.getElementById("modal-food-name").value = "";
  document.getElementById("modal-quantity").value = "1 serving";
  document.getElementById("modal-cals").value = "";
  document.getElementById("modal-p").value = "";
  document.getElementById("modal-c").value = "";
  document.getElementById("modal-f").value = "";

  document.getElementById("add-food-modal").style.display = "flex";
}

function closeAddFoodModal() {
  document.getElementById("add-food-modal").style.display = "none";
}

function onModalFoodSelect(idxStr) {
  if (idxStr === "") return;
  const food = foodCatalogue[parseInt(idxStr)];
  if (!food) return;

  document.getElementById("modal-food-name").value = food.name;
  document.getElementById("modal-quantity").value = food.serving_size;
  document.getElementById("modal-cals").value = food.calories;
  document.getElementById("modal-p").value = food.protein;
  document.getElementById("modal-c").value = food.carbs;
  document.getElementById("modal-f").value = food.fat;
}

async function saveModalFoodItem() {
  const name = document.getElementById("modal-food-name").value.trim();
  const quantity = document.getElementById("modal-quantity").value.trim();
  const cals = parseFloat(document.getElementById("modal-cals").value) || 0.0;
  const p = parseFloat(document.getElementById("modal-p").value) || 0.0;
  const c = parseFloat(document.getElementById("modal-c").value) || 0.0;
  const f = parseFloat(document.getElementById("modal-f").value) || 0.0;

  if (!name || cals <= 0) {
    alert("Please enter a valid food name and calories.");
    return;
  }

  const payload = {
    meal_type: currentModalMealType,
    items: [
      { food_name: name, quantity: quantity, calories: cals, protein: p, carbs: c, fat: f }
    ]
  };

  try {
    await API.post("/nutrition/meals", payload);
    closeAddFoodModal();
    await loadDailyNutrition();
    await loadRecommendations();
  } catch (err) {
    alert(`Failed to add food item: ${err.message}`);
  }
}

// --- Smart Recommendations ---
async function loadRecommendations() {
  const container = document.getElementById("recommendations-container");
  if (!container) return;

  try {
    const recs = await API.get("/nutrition/recommendations");
    if (!recs || recs.length === 0) {
      container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.9rem;">No recommendations currently.</div>`;
      return;
    }

    container.innerHTML = recs.map(rec => `
      <div class="card" style="background: var(--bg-primary); border-color: var(--border);">
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
          <div>
            <strong style="color: var(--text-main); font-size: 1rem;">${rec.food_name}</strong>
            <div style="font-size: 0.8rem; color: var(--text-muted);">${rec.portion} • Suggest for ${rec.suggested_meal.toUpperCase()}</div>
          </div>
          <span style="font-weight: 700; color: var(--accent); font-size: 1.1rem;">
            ${rec.calories.toFixed(0)} kcal
          </span>
        </div>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.8rem;">
          ${rec.reason}
        </p>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div style="font-size: 0.8rem; color: var(--text-muted);">
            P: ${rec.protein}g | C: ${rec.carbs}g | F: ${rec.fat}g
          </div>
          <button type="button" class="btn btn-primary btn-sm" onclick="quickAddRecommendation('${rec.food_name}', '${rec.portion}', ${rec.calories}, ${rec.protein}, ${rec.carbs}, ${rec.fat}, '${rec.suggested_meal}')">
            + Quick Add
          </button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error("Error loading recommendations:", err);
  }
}

async function quickAddRecommendation(name, portion, cals, p, c, f, mealType) {
  const payload = {
    meal_type: mealType,
    items: [
      { food_name: name, quantity: portion, calories: cals, protein: p, carbs: c, fat: f }
    ]
  };
  try {
    await API.post("/nutrition/meals", payload);
    document.getElementById("alert-container").innerHTML = `
      <div class="alert alert-success">
        Added <strong>${name}</strong> to your ${mealType.toUpperCase()}!
      </div>
    `;
    await loadDailyNutrition();
    await loadRecommendations();
  } catch (err) {
    alert(`Failed to add: ${err.message}`);
  }
}
