let pollInterval = null;

document.addEventListener("DOMContentLoaded", () => {
  if (!Auth.requireAuth(true)) return;
  loadModels();
});

async function loadModels() {
  try {
    const models = await API.get("/admin/models");
    const tbody = document.getElementById("models-tbody");
    tbody.innerHTML = "";

    if (!models || models.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted);">No trained models found.</td></tr>`;
      return;
    }

    models.forEach(m => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>v${m.id}</strong></td>
        <td><span style="color: var(--accent); font-weight: 600;">${m.algorithm}</span></td>
        <td><strong>${m.rmse.toFixed(4)}</strong></td>
        <td>${m.mae.toFixed(4)}</td>
        <td>${m.r2.toFixed(4)}</td>
        <td>${(m.clf_accuracy * 100).toFixed(1)}%</td>
        <td>${m.clf_f1.toFixed(3)}</td>
        <td>
          <span class="badge ${m.is_active ? 'badge-low' : 'badge-seed'}">
            ${m.is_active ? 'ACTIVE' : 'INACTIVE'}
          </span>
        </td>
        <td>
          ${m.is_active
            ? '<span style="color: var(--success); font-size: 0.85rem;">Currently Serving</span>'
            : `<button class="btn btn-secondary btn-sm" onclick="activateModel(${m.id})">Activate (Rollback)</button>`
          }
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading models:", err);
  }
}

async function handleUpload(e) {
  e.preventDefault();
  const fileInput = document.getElementById("csv-file");
  if (!fileInput.files.length) return;

  const file = fileInput.files[0];
  const formData = new FormData();
  formData.append("file", file);

  const resBox = document.getElementById("upload-result");
  const btn = document.getElementById("btn-upload");
  btn.disabled = true;
  btn.textContent = "Uploading & Validating...";

  try {
    const data = await API.upload("/admin/upload-data", formData);
    resBox.className = "alert alert-success";
    resBox.innerHTML = `✅ Successfully uploaded <strong>${file.name}</strong> (${data.rows} valid rows). Dataset ID: ${data.dataset_id}`;
    resBox.style.display = "block";

    // Add to dropdown
    const select = document.getElementById("retrain-dataset-id");
    const opt = document.createElement("option");
    opt.value = data.dataset_id;
    opt.textContent = `Dataset #${data.dataset_id} (${file.name}, ${data.rows} rows)`;
    opt.selected = true;
    select.appendChild(opt);
  } catch (err) {
    resBox.className = "alert alert-danger";
    resBox.textContent = "Upload rejected: " + err.message;
    resBox.style.display = "block";
  } finally {
    btn.disabled = false;
    btn.textContent = "Upload & Validate CSV";
  }
}

async function startRetrain() {
  const select = document.getElementById("retrain-dataset-id");
  const datasetId = select.value ? parseInt(select.value, 10) : null;

  const btn = document.getElementById("btn-retrain");
  btn.disabled = true;

  try {
    const data = await API.post("/admin/retrain", { dataset_id: datasetId });
    showJobStatus(data.job_id);
    pollJob(data.job_id);
  } catch (err) {
    alert("Could not start retrain: " + err.message);
    btn.disabled = false;
  }
}

function showJobStatus(jobId) {
  const box = document.getElementById("job-status-box");
  box.style.display = "block";
  box.className = "alert alert-warning";
  document.getElementById("job-id").textContent = jobId;
  document.getElementById("job-status-text").textContent = "RUNNING";
  document.getElementById("job-msg").textContent = "Training 4 models and evaluating on frozen hold-out set...";
}

function pollJob(jobId) {
  if (pollInterval) clearInterval(pollInterval);

  pollInterval = setInterval(async () => {
    try {
      const job = await API.get(`/admin/retrain/${jobId}`);
      document.getElementById("job-status-text").textContent = job.status.toUpperCase();

      if (job.status === "succeeded") {
        clearInterval(pollInterval);
        document.getElementById("btn-retrain").disabled = false;
        const box = document.getElementById("job-status-box");
        box.className = "alert alert-success";
        document.getElementById("job-msg").textContent = job.message || "Model bundle evaluated successfully.";
        loadModels();
      } else if (job.status === "failed") {
        clearInterval(pollInterval);
        document.getElementById("btn-retrain").disabled = false;
        const box = document.getElementById("job-status-box");
        box.className = "alert alert-danger";
        document.getElementById("job-msg").textContent = "Failed: " + job.message;
      }
    } catch (err) {
      console.error("Polling error:", err);
    }
  }, 2000);
}

async function activateModel(modelId) {
  if (!confirm(`Activate model v${modelId}? This will immediately switch the serving model bundle.`)) return;

  try {
    await API.post(`/admin/models/${modelId}/activate`, {});
    alert(`Model v${modelId} is now active!`);
    loadModels();
  } catch (err) {
    alert("Activation failed: " + err.message);
  }
}
