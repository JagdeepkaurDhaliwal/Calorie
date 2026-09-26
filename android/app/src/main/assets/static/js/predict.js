let currentHeightUnit = "cm";
let currentWeightUnit = "kg";
let currentTempUnit = "C";

document.addEventListener("DOMContentLoaded", async () => {
  if (!Auth.requireAuth()) return;

  // Pre-fill user profile if available
  const user = Auth.getUser();
  if (user) {
    if (user.gender) document.getElementById("gender").value = user.gender;
    if (user.age) document.getElementById("age").value = user.age;
    if (user.height_cm) document.getElementById("height").value = user.height_cm;
    if (user.weight_kg) document.getElementById("weight").value = user.weight_kg;
  }
});

function toggleHeightUnit(unit) {
  currentHeightUnit = unit;
  document.getElementById("height-cm-group").style.display = (unit === "cm") ? "block" : "none";
  document.getElementById("height-ft-group").style.display = (unit === "ft") ? "grid" : "none";
}

function toggleWeightUnit(unit) {
  currentWeightUnit = unit;
  const input = document.getElementById("weight");
  if (unit === "lbs") {
    input.value = (parseFloat(input.value || 70) * 2.20462).toFixed(1);
    input.min = "40";
    input.max = "500";
  } else {
    input.value = (parseFloat(input.value || 154) / 2.20462).toFixed(1);
    input.min = "20";
    input.max = "250";
  }
}

function toggleTempUnit(unit) {
  currentTempUnit = unit;
  const input = document.getElementById("body_temp");
  if (unit === "F") {
    input.value = ((parseFloat(input.value || 38.5) * 9/5) + 32).toFixed(1);
    input.min = "95";
    input.max = "108";
  } else {
    input.value = ((parseFloat(input.value || 101.3) - 32) * 5/9).toFixed(1);
    input.min = "35";
    input.max = "42";
  }
}

async function handlePredict(e) {
  e.preventDefault();

  const payload = {
    gender: document.getElementById("gender").value,
    age: parseInt(document.getElementById("age").value, 10),
    duration: parseFloat(document.getElementById("duration").value),
    heart_rate: parseFloat(document.getElementById("heart_rate").value),
    height_unit: currentHeightUnit,
    weight_unit: currentWeightUnit,
    body_temp_unit: currentTempUnit,
  };

  if (currentHeightUnit === "cm") {
    payload.height = parseFloat(document.getElementById("height").value);
  } else {
    payload.height_feet = parseFloat(document.getElementById("height_feet").value) || 5;
    payload.height_inches = parseFloat(document.getElementById("height_inches").value) || 9;
  }

  payload.weight = parseFloat(document.getElementById("weight").value);
  payload.body_temp = parseFloat(document.getElementById("body_temp").value);

  try {
    const result = await API.post("/predict", payload);

    document.getElementById("result-placeholder").style.display = "none";
    document.getElementById("result-content").style.display = "block";

    document.getElementById("res-calories").textContent = `${result.predicted_calories.toFixed(1)} kcal`;

    const intensityEl = document.getElementById("res-intensity");
    intensityEl.textContent = result.intensity.toUpperCase();
    intensityEl.className = `badge badge-${result.intensity.toLowerCase()}`;

    document.getElementById("res-version").textContent = result.model_version;

    const warnBox = document.getElementById("warnings-box");
    const warnList = document.getElementById("warnings-list");
    warnList.innerHTML = "";

    if (result.extrapolated && result.warnings && result.warnings.length > 0) {
      result.warnings.forEach(w => {
        const li = document.createElement("li");
        li.textContent = w;
        warnList.appendChild(li);
      });
      warnBox.style.display = "block";
    } else {
      warnBox.style.display = "none";
    }
  } catch (err) {
    alert("Prediction error: " + err.message);
  }
}
