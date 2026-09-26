// Interactive Anatomical Human Body SVG Component for CalorieCast
// Visualizes muscle groups and highlights the active/selected body part in RED (#ef4444).

const BodyMap = {
  currentPart: "chest",
  currentView: "front", // "front" or "back"
  calorieData: {},
  listeners: [],

  init(containerId, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;

    this.container = container;
    this.currentPart = options.initialPart || "chest";
    this.onSelectCallback = options.onSelect || null;
    this.calorieData = options.calorieData || {};

    this.render();
    this.highlight(this.currentPart);
  },

  onSelect(callback) {
    this.listeners.push(callback);
  },

  setCalories(bodyPartTotals = {}) {
    this.calorieData = bodyPartTotals;
    this.updateLabels();
  },

  setView(view) {
    this.currentView = view;
    this.render();
    this.highlight(this.currentPart);
  },

  selectPart(partId) {
    this.currentPart = partId;
    // Auto-switch view if needed (e.g. back or triceps are on the back view)
    if (partId === "back" || partId === "triceps") {
      this.currentView = "back";
      this.render();
    } else if (partId === "chest" || partId === "biceps") {
      this.currentView = "front";
      this.render();
    }
    this.highlight(partId);

    if (this.onSelectCallback) {
      this.onSelectCallback(partId);
    }
    this.listeners.forEach(fn => fn(partId));
  },

  highlight(partId) {
    if (!this.container) return;
    const parts = this.container.querySelectorAll(".body-part");
    parts.forEach(el => el.classList.remove("selected"));

    if (partId === "full_body") {
      parts.forEach(el => el.classList.add("selected"));
    } else {
      const match = this.container.querySelectorAll(`[data-part="${partId}"]`);
      match.forEach(el => el.classList.add("selected"));
    }

    this.updateBadge(partId);
  },

  updateBadge(partId) {
    const badgeName = document.getElementById("body-part-selected-name");
    const badgeCals = document.getElementById("body-part-selected-cals");
    if (badgeName) {
      const names = {
        chest: "Chest (Pectorals)",
        back: "Back (Lats & Traps)",
        legs: "Legs (Quads, Calves & Hamstrings)",
        biceps: "Biceps (Front Upper Arms)",
        triceps: "Triceps (Back Upper Arms)",
        shoulders: "Shoulders (Deltoids)",
        full_body: "Full Body (Compound)",
      };
      badgeName.innerHTML = `<span style="display:inline-block; width:12px; height:12px; background:#ef4444; border-radius:50%; box-shadow:0 0 8px #ef4444; margin-right:6px;"></span>${names[partId] || partId.toUpperCase()}`;
    }
    if (badgeCals) {
      const kcal = this.calorieData[partId] || 0.0;
      badgeCals.textContent = `${kcal.toFixed(1)} kcal burned today`;
    }
  },

  updateLabels() {
    this.updateBadge(this.currentPart);
    // Update any stat cards with body part calories
    for (const [part, cals] of Object.entries(this.calorieData)) {
      const el = document.getElementById(`cal-badge-${part}`);
      if (el) el.textContent = `${Number(cals).toFixed(1)} kcal`;
    }
  },

  render() {
    const isFront = this.currentView === "front";

    const svgContent = isFront ? this.getFrontSvg() : this.getBackSvg();

    this.container.innerHTML = `
      <div class="body-map-wrapper">
        <div class="body-map-toolbar">
          <div class="view-toggles">
            <button type="button" class="btn btn-sm ${isFront ? 'btn-primary' : 'btn-secondary'}" onclick="BodyMap.setView('front')">
              Front View
            </button>
            <button type="button" class="btn btn-sm ${!isFront ? 'btn-primary' : 'btn-secondary'}" onclick="BodyMap.setView('back')">
              Back View
            </button>
          </div>
          <button type="button" class="btn btn-sm btn-secondary ${this.currentPart === 'full_body' ? 'active-fb' : ''}" onclick="BodyMap.selectPart('full_body')">
            ⚡ Full Body
          </button>
        </div>

        <div class="svg-container">
          ${svgContent}
        </div>

        <div class="body-part-info-card">
          <div id="body-part-selected-name" class="part-name">Loading...</div>
          <div id="body-part-selected-cals" class="part-cals">0.0 kcal burned today</div>
        </div>

        <div class="body-parts-quick-grid">
          <button type="button" class="quick-chip ${this.currentPart === 'chest' ? 'active' : ''}" onclick="BodyMap.selectPart('chest')">Chest <span id="cal-badge-chest" class="chip-cal">0 kcal</span></button>
          <button type="button" class="quick-chip ${this.currentPart === 'back' ? 'active' : ''}" onclick="BodyMap.selectPart('back')">Back <span id="cal-badge-back" class="chip-cal">0 kcal</span></button>
          <button type="button" class="quick-chip ${this.currentPart === 'legs' ? 'active' : ''}" onclick="BodyMap.selectPart('legs')">Legs <span id="cal-badge-legs" class="chip-cal">0 kcal</span></button>
          <button type="button" class="quick-chip ${this.currentPart === 'shoulders' ? 'active' : ''}" onclick="BodyMap.selectPart('shoulders')">Shoulders <span id="cal-badge-shoulders" class="chip-cal">0 kcal</span></button>
          <button type="button" class="quick-chip ${this.currentPart === 'biceps' ? 'active' : ''}" onclick="BodyMap.selectPart('biceps')">Biceps <span id="cal-badge-biceps" class="chip-cal">0 kcal</span></button>
          <button type="button" class="quick-chip ${this.currentPart === 'triceps' ? 'active' : ''}" onclick="BodyMap.selectPart('triceps')">Triceps <span id="cal-badge-triceps" class="chip-cal">0 kcal</span></button>
        </div>
      </div>
    `;

    // Attach click events on SVG parts
    const parts = this.container.querySelectorAll(".body-part");
    parts.forEach(el => {
      el.addEventListener("click", (e) => {
        e.stopPropagation();
        const part = el.getAttribute("data-part");
        if (part) this.selectPart(part);
      });
    });

    this.updateLabels();
  },

  getFrontSvg() {
    return `
      <svg viewBox="0 0 300 450" class="human-body-svg" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id="glow-red" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="0" stdDeviation="6" flood-color="#ef4444" flood-opacity="0.9" />
          </filter>
        </defs>

        <!-- Head & Neck -->
        <ellipse cx="150" cy="40" rx="22" ry="28" class="body-silhouette" />
        <rect x="142" y="65" width="16" height="18" rx="4" class="body-silhouette" />

        <!-- Shoulders (Deltoids) -->
        <g class="body-part" data-part="shoulders">
          <path d="M 118,84 C 104,86 92,96 89,112 C 96,118 108,118 114,106 C 117,100 118,92 118,84 Z" />
          <path d="M 182,84 C 196,86 208,96 211,112 C 204,118 192,118 186,106 C 183,100 182,92 182,84 Z" />
        </g>

        <!-- Chest (Pectorals) -->
        <g class="body-part" data-part="chest">
          <path d="M 120,85 C 135,83 148,86 150,88 C 152,86 165,83 180,85 C 184,106 182,128 150,133 C 118,128 116,106 120,85 Z" />
          <line x1="150" y1="88" x2="150" y2="132" stroke="#1e293b" stroke-width="2" />
        </g>

        <!-- Biceps (Front Upper Arms) -->
        <g class="body-part" data-part="biceps">
          <path d="M 89,114 C 82,128 82,154 90,166 C 96,166 104,156 107,138 C 109,126 101,116 89,114 Z" />
          <path d="M 211,114 C 218,128 218,154 210,166 C 204,166 196,156 193,138 C 191,126 199,116 211,114 Z" />
        </g>

        <!-- Forearms & Hands -->
        <path d="M 90,168 C 86,186 80,212 78,226 C 83,229 88,226 93,208 C 97,192 101,176 103,168 Z" class="body-silhouette" />
        <path d="M 210,168 C 214,186 220,212 222,226 C 217,229 212,226 207,208 C 203,192 199,176 197,168 Z" class="body-silhouette" />
        <ellipse cx="76" cy="235" rx="7" ry="10" class="body-silhouette" />
        <ellipse cx="224" cy="235" rx="7" ry="10" class="body-silhouette" />

        <!-- Abdominals & Torso Core -->
        <path d="M 124,135 C 126,155 124,185 118,206 C 135,211 165,211 182,206 C 176,185 174,155 176,135 C 160,137 140,137 124,135 Z" class="body-silhouette" />

        <!-- Legs (Quads & Calves) -->
        <g class="body-part" data-part="legs">
          <!-- Left & Right Quads -->
          <path d="M 118,208 C 113,235 110,275 116,310 C 128,312 142,305 144,275 C 146,245 146,218 144,208 Z" />
          <path d="M 182,208 C 187,235 190,275 184,310 C 172,312 158,305 156,275 C 154,245 154,218 156,208 Z" />
          <!-- Left & Right Calves & Ankles -->
          <path d="M 117,314 C 112,345 114,385 120,415 C 126,416 134,412 136,390 C 138,360 140,330 139,314 Z" />
          <path d="M 183,314 C 188,345 186,385 180,415 C 174,416 166,412 164,390 C 162,360 160,330 161,314 Z" />
          <!-- Feet -->
          <ellipse cx="120" cy="425" rx="10" ry="7" />
          <ellipse cx="180" cy="425" rx="10" ry="7" />
        </g>
      </svg>
    `;
  },

  getBackSvg() {
    return `
      <svg viewBox="0 0 300 450" class="human-body-svg" xmlns="http://www.w3.org/2000/svg">
        <!-- Head & Neck Posterior -->
        <ellipse cx="150" cy="40" rx="22" ry="28" class="body-silhouette" />
        <rect x="142" y="65" width="16" height="18" rx="4" class="body-silhouette" />

        <!-- Shoulders (Posterior Deltoids) -->
        <g class="body-part" data-part="shoulders">
          <path d="M 118,84 C 104,86 92,96 89,112 C 96,118 108,118 114,106 C 117,100 118,92 118,84 Z" />
          <path d="M 182,84 C 196,86 208,96 211,112 C 204,118 192,118 186,106 C 183,100 182,92 182,84 Z" />
        </g>

        <!-- Back (Lats, Trapezius & Rhomboids) -->
        <g class="body-part" data-part="back">
          <path d="M 135,76 L 150,82 L 165,76 C 176,92 184,118 178,165 C 165,188 152,198 150,199 C 148,198 135,188 122,165 C 116,118 124,92 135,76 Z" />
          <line x1="150" y1="82" x2="150" y2="198" stroke="#1e293b" stroke-width="2" />
        </g>

        <!-- Triceps (Back Upper Arms) -->
        <g class="body-part" data-part="triceps">
          <path d="M 89,114 C 82,130 82,156 90,168 C 96,168 104,158 107,140 C 109,126 101,116 89,114 Z" />
          <path d="M 211,114 C 218,130 218,156 210,168 C 204,168 196,158 193,140 C 191,126 199,116 211,114 Z" />
        </g>

        <!-- Forearms Posterior -->
        <path d="M 90,168 C 86,186 80,212 78,226 C 83,229 88,226 93,208 C 97,192 101,176 103,168 Z" class="body-silhouette" />
        <path d="M 210,168 C 214,186 220,212 222,226 C 217,229 212,226 207,208 C 203,192 199,176 197,168 Z" class="body-silhouette" />
        <ellipse cx="76" cy="235" rx="7" ry="10" class="body-silhouette" />
        <ellipse cx="224" cy="235" rx="7" ry="10" class="body-silhouette" />

        <!-- Lower Back & Glutes -->
        <path d="M 124,198 C 126,205 125,215 118,220 C 135,225 165,225 182,220 C 175,215 174,205 176,198 Z" class="body-silhouette" />

        <!-- Legs (Hamstrings, Posterior Calves) -->
        <g class="body-part" data-part="legs">
          <path d="M 118,220 C 113,245 110,285 116,310 C 128,312 142,305 144,275 C 146,245 146,225 144,220 Z" />
          <path d="M 182,220 C 187,245 190,285 184,310 C 172,312 158,305 156,275 C 154,245 154,225 156,220 Z" />
          <path d="M 117,314 C 112,345 114,385 120,415 C 126,416 134,412 136,390 C 138,360 140,330 139,314 Z" />
          <path d="M 183,314 C 188,345 186,385 180,415 C 174,416 166,412 164,390 C 162,360 160,330 161,314 Z" />
          <ellipse cx="120" cy="425" rx="10" ry="7" />
          <ellipse cx="180" cy="425" rx="10" ry="7" />
        </g>
      </svg>
    `;
  }
};
