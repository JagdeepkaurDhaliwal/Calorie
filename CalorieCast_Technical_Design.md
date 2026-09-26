# CalorieCast: System Technical Design (STD)

| Field | Details |
|---|---|
| **Project** | CalorieCast: Real-Time Calories Burnt Prediction and Forecasting System |
| **Document version** | 1.0 |
| **Date** | 24 September 2026 |
| **Author** | [Your Name], BCA 4th Semester |
| **Institution** | [College / University Name] |
| **Derived from** | CalorieCast PRD v1.0 and CalorieCast SRS v1.0 |
| **Audience** | Developer (you), project guide, evaluators |

**Purpose of this document:** The PRD says *what* the product is for, and the SRS says *what the system must do*. This document says *how it will be built*: architecture, modules, database, ML pipeline, API contract, real-time protocol, security, testing, and deployment. If you follow it in order, you can build the whole project without making major design decisions on the fly.

---

## 1. Design Goals and Principles

| Goal | How the design achieves it |
|---|---|
| **Backend-focused** | Most logic lives in services (prediction, forecast, sessions, retraining). The frontend is thin and only calls the API. |
| **Buildable in about 3 weeks by one person** | Modular monolith, SQLite, no external services, one command for training. |
| **Demonstrably ML/DL** | Four regression models compared, a classifier, an ANN, a model registry, and safe retraining. |
| **Honest and safe** | Out-of-range warnings, seeded data clearly labelled, and a new model is activated only if it is better. |
| **Easy to explain in a viva** | Layered architecture with one clear responsibility per module. |

**Principles**
1. Routers stay thin: validate, call a service, return a response.
2. Services hold the business logic and know nothing about HTTP.
3. ML code lives in `ml/` and is reused by both the training script and the API, so training and serving use identical preprocessing.
4. Every prediction records which model version made it.
5. Fail safe: if anything goes wrong with a new model, the old one keeps serving.

---

## 2. Architecture

### 2.1 Architectural Style
A **layered modular monolith**: one FastAPI application with clearly separated layers, a shared database, and an in-process model registry. This is the simplest architecture that still shows good engineering, and it can run on a laptop.

### 2.2 Layered View

```
+---------------------------------------------------------------+
|  PRESENTATION   Static frontend (HTML, Bootstrap, JS, Chart.js)|
+-------------------------------+-------------------------------+
                                | HTTP (REST/JSON), WebSocket
+-------------------------------v-------------------------------+
|  API LAYER      FastAPI routers + Pydantic schemas             |
|                 auth | predict | workouts | forecast | sessions |
|                 admin | health                                 |
|                 Middleware: error handler, logging, CORS       |
+-------------------------------+-------------------------------+
                                |
+-------------------------------v-------------------------------+
|  SERVICE LAYER  auth_service | prediction_service |            |
|                 workout_service | forecast_service |           |
|                 session_service | admin_service (retrain jobs) |
+---------------+---------------------------+-------------------+
                |                           |
+---------------v-----------+   +-----------v-------------------+
|  ML LAYER                 |   |  DATA LAYER                   |
|  model_registry (in-mem)  |   |  SQLAlchemy ORM models        |
|  preprocess, features     |   |  repositories / queries       |
|  train, evaluate          |   |  SQLite (MySQL/PostgreSQL     |
|  artifacts on disk        |   |  later by config change)      |
+---------------------------+   +-------------------------------+
```

### 2.3 Runtime View
- One **Uvicorn** process serves the REST API, the WebSocket endpoint, and the static frontend.
- On startup the app: creates tables if missing, ensures an admin user exists (from environment variables), and loads the **active model bundle** into memory.
- Retraining runs as a **background task**, so the API stays responsive. Its progress is stored in a `training_jobs` table.
- The prototype is designed for a **single process**. Session state that is needed across requests is stored in the database, and only a small cache is kept in memory.

### 2.4 Key Design Decisions

| # | Decision | Reason | Trade-off |
|---|---|---|---|
| D1 | Modular monolith, not microservices | Fits one developer and 3 weeks | Less scalable (acceptable for a prototype) |
| D2 | FastAPI | Async support for WebSocket, automatic Swagger docs, Pydantic validation | Slightly newer than Flask, but well documented |
| D3 | SQLite through SQLAlchemy | Zero setup; a config change moves to MySQL/PostgreSQL | Limited concurrency; free hosts may reset the file |
| D4 | Bundle-based model versions | One version = regressor + classifier + scaler + metadata, so they can never get out of sync | Slightly larger artifact folder |
| D5 | Frozen hold-out test set | New and old models are compared on identical data, so the comparison is fair | New uploaded data only trains; it is not used for testing |
| D6 | Background retraining with job table | Avoids HTTP timeouts and shows good backend practice | A little more code |
| D7 | Server-side elapsed-time accounting in live sessions | Simple and works with simulated streams | Client can influence the time it reports (fine for a prototype) |
| D8 | Static frontend served by FastAPI | One server, no CORS issues | No frontend framework features (not needed) |

---

## 3. Technology Stack

| Area | Choice | Notes |
|---|---|---|
| Language | Python 3.10+ | |
| Web framework | FastAPI + Uvicorn | REST and WebSocket, Swagger at `/docs` |
| Validation | Pydantic v2 | Request and response schemas |
| ORM / DB | SQLAlchemy 2.x, SQLite | `DATABASE_URL` decides the database |
| Auth | PyJWT (HS256) + bcrypt | Access tokens with expiry |
| ML | pandas, NumPy, scikit-learn, TensorFlow/Keras, joblib | Keras only for the ANN |
| Config | pydantic-settings + `.env` | No secrets in code |
| Frontend | HTML, Bootstrap 5, vanilla JS, Chart.js | CDN links are acceptable |
| Testing | pytest, FastAPI TestClient, httpx | In-memory SQLite for tests |
| Tooling | Git/GitHub, VS Code, Google Colab, Postman or Swagger UI | |

`requirements.txt` (pin the versions you actually installed):
```
fastapi
uvicorn[standard]
sqlalchemy
pydantic-settings
pyjwt
bcrypt
pandas
numpy
scikit-learn
tensorflow
joblib
python-multipart
pytest
httpx
```

---

## 4. Code Structure

```
caloriecast/
├── app/
│   ├── main.py                 # app factory, startup hooks, router mounting
│   ├── config.py               # Settings (env vars)
│   ├── database.py             # engine, SessionLocal, get_db dependency
│   ├── models.py               # SQLAlchemy tables
│   ├── schemas.py              # Pydantic request/response models
│   ├── security.py             # hashing, JWT create/verify, get_current_user, require_admin
│   ├── errors.py               # custom exceptions + handlers (error envelope)
│   ├── routers/
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── predict.py
│   │   ├── workouts.py
│   │   ├── forecast.py
│   │   ├── sessions.py         # REST + WebSocket
│   │   └── admin.py
│   └── services/
│       ├── prediction_service.py
│       ├── workout_service.py
│       ├── forecast_service.py
│       ├── session_service.py
│       └── admin_service.py    # upload validation, retrain orchestration
├── ml/
│   ├── config.py               # feature list, ranges, hyper-parameters, seeds
│   ├── preprocess.py           # cleaning, encoding, splitting
│   ├── features.py             # build_features(profile, workout) -> DataFrame
│   ├── train.py                # trains and evaluates all models, writes a bundle
│   ├── evaluate.py             # metrics, confusion matrix, plots
│   ├── registry.py             # loads/holds the active bundle, hot-swap
│   └── artifacts/              # v1/, v2/, ... (model files + meta.json)
├── data/
│   ├── raw/                    # exercise.csv, calories.csv
│   ├── holdout.csv             # frozen test set (created once)
│   └── uploads/                # admin-uploaded CSVs (uuid file names)
├── scripts/
│   ├── bootstrap_train.py      # first-time training and activation
│   ├── create_admin.py
│   ├── seed_demo_data.py       # sample history for demo users (labelled 'seed')
│   └── simulate_stream.py      # fake heart-rate stream for live sessions
├── frontend/
│   ├── index.html, login.html, predict.html, dashboard.html,
│   │   live.html, admin.html
│   ├── css/style.css
│   └── js/api.js, auth.js, predict.js, dashboard.js, live.js, admin.js
├── tests/
├── notebooks/                  # Colab experiments (EDA, model comparison)
├── .env.example
├── requirements.txt
└── README.md
```

**Dependency rule:** `routers → services → (ml, database)`. Routers never touch the database or models directly, and services never import FastAPI.

---

## 5. Data Design

### 5.1 Entity Relationship Overview

```
users 1 ----< workouts >---- 1 model_versions
users 1 ----< sessions 1 ----< readings
users 1 ----< datasets (uploaded_by)
datasets 1 ----< training_jobs >---- 0..1 model_versions
```

### 5.2 Tables

**users**

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| name | VARCHAR(100) | NOT NULL |
| email | VARCHAR(255) | UNIQUE, NOT NULL, indexed |
| password_hash | VARCHAR(255) | NOT NULL |
| role | VARCHAR(10) | NOT NULL, default `user`, CHECK in (`user`,`admin`) |
| age | INTEGER | nullable |
| gender | VARCHAR(10) | nullable, CHECK in (`male`,`female`) |
| height_cm | FLOAT | nullable |
| weight_kg | FLOAT | nullable |
| created_at | DATETIME | default now (UTC) |

**workouts**

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| user_id | INTEGER | FK → users.id, NOT NULL, indexed |
| duration_min | FLOAT | NOT NULL |
| heart_rate | FLOAT | NOT NULL (average bpm) |
| body_temp | FLOAT | NOT NULL |
| predicted_calories | FLOAT | NOT NULL |
| intensity | VARCHAR(10) | NOT NULL |
| model_version_id | INTEGER | FK → model_versions.id |
| source | VARCHAR(10) | NOT NULL: `manual`, `session`, or `seed` |
| extrapolated | BOOLEAN | default false |
| created_at | DATETIME | NOT NULL |

Index: `(user_id, created_at DESC)`.

**sessions**

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| user_id | INTEGER | FK, NOT NULL, indexed |
| status | VARCHAR(10) | `active` or `ended` |
| started_at | DATETIME | NOT NULL |
| ended_at | DATETIME | nullable |
| elapsed_sec | INTEGER | default 0 |
| hr_sum | FLOAT | default 0 (running sum for the average) |
| reading_count | INTEGER | default 0 |
| body_temp_input | FLOAT | nullable (optional user value) |
| total_calories | FLOAT | nullable until ended |
| intensity | VARCHAR(10) | nullable until ended |

**readings**

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| session_id | INTEGER | FK, NOT NULL |
| heart_rate | INTEGER | NOT NULL |
| interval_sec | INTEGER | NOT NULL (time this reading represents) |
| elapsed_sec | INTEGER | NOT NULL (running total after this reading) |
| cumulative_calories | FLOAT | NOT NULL |
| timestamp | DATETIME | NOT NULL |

Index: `(session_id, timestamp)`.

**model_versions** (one row = one trained *bundle*)

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PK (also the artifact folder number, `v{id}`) |
| algorithm | VARCHAR(50) | Winning regressor name (this is `name` in the SRS) |
| artifact_dir | VARCHAR(255) | e.g. `ml/artifacts/v3` |
| mae, rmse, r2 | FLOAT | Winner's metrics on the frozen hold-out set |
| clf_accuracy, clf_f1 | FLOAT | Intensity classifier metrics |
| candidates_json | TEXT | Metrics of all 4 regressors (for the comparison table) |
| training_job_id | INTEGER | FK, nullable (null for bootstrap) |
| is_active | BOOLEAN | Only one row may be true |
| created_at | DATETIME | |

Constraint: a **partial unique index** on `is_active` where `is_active = 1` guarantees only one active version (SQLite and PostgreSQL both support partial indexes).

**datasets** (added for admin uploads)

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PK |
| original_name | VARCHAR(255) | As uploaded |
| stored_path | VARCHAR(255) | `data/uploads/<uuid>.csv` |
| row_count | INTEGER | After validation |
| status | VARCHAR(15) | `valid` / `rejected` |
| message | TEXT | Reason if rejected |
| uploaded_by | INTEGER | FK → users.id |
| uploaded_at | DATETIME | |

**training_jobs** (added for background retraining)

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PK |
| dataset_id | INTEGER | FK, nullable (null = base data only) |
| status | VARCHAR(15) | `queued` / `running` / `succeeded` / `failed` |
| message | TEXT | Error text or outcome (for example "candidate not better; not activated") |
| model_version_id | INTEGER | FK, nullable, filled on success |
| activated | BOOLEAN | Whether the new version became active |
| started_at, finished_at | DATETIME | |

### 5.3 Data Rules
- All timestamps are stored in **UTC**.
- Users can only read and delete rows where `user_id` equals their own id. Every query in `workout_service` and `session_service` filters by `user_id`.
- Weeks for the forecast are **ISO weeks (Monday to Sunday)** computed in UTC.
- Use SQLAlchemy migrations (Alembic) only if you have time; otherwise `Base.metadata.create_all()` on startup is enough for the prototype.

---

## 6. Machine Learning Design

### 6.1 Data Specification
- **Source:** Kaggle "Calories Burnt Prediction": `exercise.csv` (User_ID, Gender, Age, Height, Weight, Duration, Heart_Rate, Body_Temp) merged with `calories.csv` (User_ID, Calories) on `User_ID`.
- **Model inputs (7 features, fixed order):** `gender, age, height, weight, duration, heart_rate, body_temp`.
- **Target:** `calories` (kcal).
- **Important:** In this dataset, duration, heart rate, and body temperature cover only a narrow band (for example, duration up to about 30 minutes). Confirm the exact minimum and maximum of every column with `df.describe()` in Phase 2. The API accepts wider ranges (SRS Section 3.3.1), so the design includes an **extrapolation warning** (Section 6.8).

### 6.2 Preprocessing Pipeline (`ml/preprocess.py`)
1. Merge the two CSVs, drop `User_ID`, and remove duplicates.
2. Handle missing values (drop rows if very few, otherwise median fill).
3. Encode `gender`: `male = 0`, `female = 1`.
4. Check and cap or remove obvious outliers using the SRS ranges.
5. **Frozen split (done once):** create `data/holdout.csv` with 20% of the *base* data using `random_state=42`. It is never used for training. If the file already exists, reuse it.
6. Remaining 80% is the training pool. It is split again (for example 90/10) for validation during ANN training only.
7. Fit `StandardScaler` on the training data only, then apply it to validation and hold-out data.
8. Save feature order, scaler, and the training min/max of each feature into the bundle metadata.

Training and serving both call the same `features.build_features()`, which returns a one-row DataFrame in the saved feature order. This removes the most common ML deployment bug: train/serve mismatch.

### 6.3 Regression Models

| Model | Configuration | Notes |
|---|---|---|
| Linear Regression | defaults | Baseline |
| Random Forest Regressor | `n_estimators=200`, `random_state=42` | Often the strongest on tabular data |
| KNN Regressor | `k` chosen by GridSearchCV over 3 to 15 | Needs scaled data |
| ANN (Keras) | Input(7) → Dense(64, ReLU) → Dense(32, ReLU) → Dense(1); Adam (lr 1e-3), MSE loss, batch 32, up to 200 epochs, EarlyStopping (patience 10, restore best weights) | Requirement: ANN comparison |

**Selection rule:** the winner is the model with the **lowest RMSE on the frozen hold-out set**. MAE and R² are also recorded. All four results are saved in `candidates_json`, so the admin page can show the comparison table.

### 6.4 Intensity Classification
1. Compute `kcal_per_min = calories / duration` on the training pool.
2. Compute the 33rd and 66th percentile thresholds `t1`, `t2` from the **training pool only**.
3. Labels: `low` if below `t1`, `moderate` if between `t1` and `t2`, `high` if above `t2`.
4. Train a classifier on the same 7 features (they do **not** include calories, so there is no target leakage). Compare KNN Classifier and Random Forest Classifier by macro F1 on the hold-out set, and keep the better one.
5. Save `t1`, `t2` in metadata (useful for explaining the labels to users).
6. Report accuracy, precision, recall, F1, and the confusion matrix.

### 6.5 Model Bundle (artifact layout)

```
ml/artifacts/v3/
├── regressor.joblib        # or regressor.keras when the ANN wins
├── classifier.joblib
├── scaler.joblib
├── temp_model.joblib       # auxiliary body-temperature estimator (Section 6.7)
└── meta.json
```

`meta.json` example:
```json
{
  "version": 3,
  "created_at": "2026-09-24T10:30:00Z",
  "feature_order": ["gender","age","height","weight","duration","heart_rate","body_temp"],
  "feature_ranges": {"duration": [1, 30], "heart_rate": [67, 128], "body_temp": [37.1, 41.5]},
  "intensity_thresholds": {"t1": 4.1, "t2": 7.3},
  "regressor": {"algorithm": "RandomForest", "mae": 1.7, "rmse": 2.5, "r2": 0.998},
  "classifier": {"algorithm": "RandomForestClassifier", "accuracy": 0.94, "f1_macro": 0.94},
  "candidates": {"LinearRegression": {}, "RandomForest": {}, "KNN": {}, "ANN": {}}
}
```
The numbers above are placeholders to show the format, not real results.

### 6.6 Model Registry (`ml/registry.py`)

Responsibilities:
- Hold one `LoadedModel` object in memory (regressor, classifier, scaler, temp model, meta).
- `active()` returns it (thread-safe read).
- `reload(version_id)` loads a bundle from disk and swaps the reference under a lock (**hot swap**, no server restart).
- If loading fails, keep the previous model and log the error (NFR-11).

**Activation algorithm** (`admin_service.try_activate`):

```python
def try_activate(db, new_version) -> bool:
    active = db.query(ModelVersion).filter_by(is_active=True).first()
    better = active is None or new_version.rmse < active.rmse
    if not better:
        return False                      # saved but inactive
    with db.begin_nested():               # one atomic transaction
        if active:
            active.is_active = False
        new_version.is_active = True
    registry.reload(new_version.id)       # only after DB commit succeeds
    return True
```
Both models were evaluated on the same frozen hold-out set, so the comparison is fair (decision D5). Rollback (FR-36) is the same function with a chosen older version, without the "better" check.

### 6.7 Live Session Calorie Method (ML-9)

The regressor predicts the total calories for a *finished* workout. To show running calories during a session, the design re-uses it as follows.

At every reading:
1. `elapsed_sec += interval_sec`, `hr_sum += heart_rate`, `reading_count += 1`.
2. `elapsed_min = elapsed_sec / 60`, `avg_hr = hr_sum / reading_count`.
3. `body_temp`: if the user supplied one at session start, use it. Otherwise estimate it with the auxiliary **temperature model** (a small linear regression trained on the same dataset: `body_temp ~ duration + heart_rate`, saved as `temp_model.joblib`).
4. `cumulative_calories = regressor.predict(profile, duration=max(elapsed_min, 1), avg_hr, body_temp)`; if `elapsed_min < 1`, scale the result by `elapsed_min` so the counter starts near zero.
5. Enforce monotonic growth: `cumulative = max(cumulative, previous_cumulative)`, so the number never drops on screen when average heart rate dips.

At session end, the same calculation gives `total_calories` and the intensity label. The session is also saved as a workout row with `source = 'session'`.

**Limitations to state in your report:** this is a model-based approximation, not a sensor-based measurement, and predictions for sessions longer than the training range are extrapolations.

### 6.8 Training-Range Check (extrapolation warning)

For every prediction, compare each numeric input to `feature_ranges` in the metadata. If any value is outside its range, the response still returns a result, but includes:
```json
{ "extrapolated": true,
  "warnings": ["duration 60 min is outside the training range (1-30 min); treat this estimate as approximate"] }
```
The workout row stores `extrapolated = true`. This handles the gap between what the API accepts and what the model has seen.

### 6.9 Weekly Forecast Algorithm (`forecast_service`)

Inputs: the user's workouts grouped by ISO week (complete weeks only, up to the last 8).

```python
def weekly_forecast(db, user):
    totals = weekly_totals(db, user.id, last_n=8)      # oldest -> newest
    if len(totals) >= 3:
        weekly = ema(totals, alpha=0.5)                # exponential moving average
        method = "history"
    else:
        weekly = fallback_weekly(db, user)
        method = "fallback"
    shares = weekday_shares(db, user.id) or [1/7] * 7  # Mon..Sun share of weekly burn
    return {"method": method,
            "weekly_total": round(weekly, 1),
            "daily": [round(weekly * s, 1) for s in shares]}
```

- **EMA:** `s_1 = x_1`, `s_t = alpha * x_t + (1 - alpha) * s_(t-1)`; the forecast is the last `s_t`.
- **Optional upgrade (Could):** with 6 or more weeks, fit a Ridge regression on the last three weekly totals as lag features, and compare it with the EMA.
- **Fallback (too little history):**
  - If the user has any workouts: `weekly = mean(calories of last 10 workouts) * average workouts per week`.
  - If none: a default routine of 3 sessions per week, each 30 minutes, at `heart_rate = 0.65 * (220 - age)` (a moderate-effort assumption), with the model's predicted calories. If the profile is incomplete, use the training-set median heart rate.
- **Evaluation for the report:** on seeded users, run a rolling-origin backtest and compare EMA against the naive baseline "same as last week" using MAE. Report both honestly.

### 6.10 Seed Data (`scripts/seed_demo_data.py`)
Creates 5 demo users, each with about 8 weeks of workouts following a weekday pattern (for example Mon/Wed/Fri) with random variation. Calories come from the active model. Every row has `source = 'seed'`, and the dashboard shows a small "demo data" label for such rows. This is what makes the forecast demonstrable, and the report must say that it is synthetic.

### 6.11 Retraining Flow (`train.py`, called by `admin_service`)
1. Load base training pool (+ the uploaded dataset if given, after validation).
2. Fit the scaler and train the 4 regressors and the classifiers.
3. Evaluate everything on the **frozen hold-out set**.
4. Choose the winners and write the bundle to `ml/artifacts/v{id}/`.
5. Insert the `model_versions` row.
6. Call `try_activate`. Record the outcome in `training_jobs.message`.
7. On any exception: set the job to `failed`, keep the old active model, and delete the half-written artifact folder.

---

## 7. Backend Module Design

### 7.1 Authentication and Authorization (`security.py`, `auth_service`)

- **Registration:** validate the email format and password rules (minimum 8 characters), check that the email is unique, hash with bcrypt, and insert with role `user`.
- **Login:** find the user, verify the hash, and issue a JWT.
- **Token claims:** `sub` (user id), `role`, `exp` (default 60 minutes), `iat`. Algorithm HS256, secret from `JWT_SECRET`.
- **Dependencies:**

```python
def get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)) -> User:
    payload = decode_jwt(token)              # raises 401 if invalid or expired
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise Unauthorized()
    return user

def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise Forbidden()
    return user
```

- Admin users are created only with `scripts/create_admin.py` (reads email and password from environment variables or prompts). There is **no public way** to become an admin.

### 7.2 Prediction Service (`prediction_service`)

```python
def predict(user, payload) -> PredictionResult:
    m = registry.active()                                 # LoadedModel
    x = build_features(gender=payload.gender, age=payload.age,
                       height=payload.height, weight=payload.weight,
                       duration=payload.duration, heart_rate=payload.heart_rate,
                       body_temp=payload.body_temp, meta=m.meta)
    kcal = max(float(m.regressor_predict(x)), 0.0)
    intensity = str(m.classifier.predict(x)[0])
    warnings = m.range_warnings(payload)
    return PredictionResult(kcal, intensity, m.version_id, bool(warnings), warnings)
```

The router then saves a `workouts` row (`source='manual'`) through `workout_service` and returns the response. If the request omits profile fields, they are taken from the user's saved profile; if neither has them, the API returns `422`.

### 7.3 Workout Service
- `list(user_id, page, page_size)`: newest first, returns `items` and `total`.
- `delete(user_id, workout_id)`: returns `404` if the row does not exist or belongs to someone else (do not reveal that it exists).
- `summary(user_id)`: total calories this ISO week and average calories per workout (FR-18).

### 7.4 Session Service and WebSocket (`session_service`, `routers/sessions.py`)

**States:** `active → ended` (no other transitions).

**REST endpoints**
- `POST /sessions/start` body: `{ "body_temp": 39.5 }` (optional). Creates the session with `status='active'` and returns `{session_id, started_at}`. A user may have **only one active session** at a time (return `409` otherwise).
- `POST /sessions/{id}/end` finalizes the session (same logic as the WebSocket `end` message), saves a `workouts` row, and returns the summary.

**WebSocket protocol** (`WS /sessions/{id}/stream?token=<JWT>`)

| Direction | Message | Meaning |
|---|---|---|
| Client → server | `{"type":"reading","heart_rate":112,"interval_sec":5}` | One heart-rate reading. `interval_sec` (1 to 60, default 5) is the time this reading represents. |
| Server → client | `{"type":"update","elapsed_sec":125,"avg_hr":108.4,"cumulative_calories":18.6,"intensity_so_far":"moderate"}` | Sent after every reading |
| Client → server | `{"type":"end"}` | Finish the session |
| Server → client | `{"type":"summary","total_calories":42.1,"duration_min":6.5,"avg_hr":111.2,"intensity":"moderate"}` | Final result, then the server closes the connection |
| Server → client | `{"type":"error","code":"INVALID_READING","message":"..."}` | Bad message; connection stays open if recoverable |

**Close codes:** `4401` invalid or missing token, `4403` session belongs to another user, `4404` session not found, `4409` session already ended.

**Handler outline**
```python
@router.websocket("/sessions/{session_id}/stream")
async def stream(ws: WebSocket, session_id: int, token: str):
    user = authenticate_ws(token)            # close 4401 if invalid
    session = load_owned_active_session(session_id, user)   # 4403/4404/4409
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_json()
            if msg["type"] == "reading":
                update = session_service.add_reading(session, msg)   # validates, stores, computes
                await ws.send_json({"type": "update", **update})
            elif msg["type"] == "end":
                summary = session_service.finish(session)
                await ws.send_json({"type": "summary", **summary})
                await ws.close()
                break
    except WebSocketDisconnect:
        pass       # session stays 'active'; user can reconnect or end it via REST
```

**Polling fallback (if WebSockets are a problem on the host):** `POST /sessions/{id}/readings` (same body as the `reading` message) returns the `update` object. The frontend calls it every few seconds. `add_reading` is shared, so both routes use the same logic.

**Stale sessions:** sessions that stay `active` for more than 3 hours can be closed by a cleanup function on startup (nice to have).

### 7.5 Admin Service

**Dataset upload (`POST /admin/upload-data`, multipart CSV)**
1. Check file extension and size (`MAX_UPLOAD_MB`, default 10).
2. Save under a **uuid file name** in `data/uploads/`, never using the original file name as a path.
3. Read with pandas and validate: required columns present, numeric types, no more than 5% missing values, values within SRS ranges, and gender values valid.
4. Insert a `datasets` row (`valid` or `rejected` with a message) and return a summary (row count, issues).

**Retrain (`POST /admin/retrain`, body: `{"dataset_id": 4}` optional)**
1. Insert a `training_jobs` row with status `queued` and return `202` with `job_id`.
2. A FastAPI `BackgroundTasks` function runs the retraining flow (Section 6.11) and updates the job.
3. Only one job may run at a time (return `409` if another is `queued` or `running`).
4. `GET /admin/retrain/{job_id}` returns status, message, metrics, and whether the model was activated.

**Model management**
- `GET /admin/models`: all versions with metrics, active flag, and the four-model comparison from `candidates_json`.
- `POST /admin/models/{id}/activate`: rollback (FR-36), the "Could" item.

---

## 8. API Contract

### 8.1 Conventions
- Base path: `/` (no version prefix for the prototype). JSON in and out. Auth header: `Authorization: Bearer <token>`.
- Pagination: `?page=1&page_size=20` (max 100). Response: `{"items":[...],"total":57,"page":1,"page_size":20}`.
- Timestamps are ISO 8601 in UTC.

### 8.2 Error Envelope (all errors)
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "heart_rate must be between 40 and 220",
    "details": [{"field": "heart_rate", "issue": "value 400 out of range"}]
  }
}
```

| HTTP | `code` | When |
|---|---|---|
| 400 | `BAD_REQUEST` | Malformed request or business rule violation |
| 401 | `UNAUTHORIZED` | Missing, invalid, or expired token; wrong login |
| 403 | `FORBIDDEN` | Not an admin, or not the owner |
| 404 | `NOT_FOUND` | Resource missing (or not yours) |
| 409 | `CONFLICT` | Duplicate email, second active session, retrain already running |
| 422 | `VALIDATION_ERROR` | Field validation failed (Pydantic) |
| 500 | `INTERNAL_ERROR` | Unexpected error (details only in logs) |

### 8.3 Endpoint Details

| Method | Path | Auth | Request body / params | Success response |
|---|---|---|---|---|
| POST | `/auth/register` | none | `{name, email, password}` | `201 {id, name, email, role}` |
| POST | `/auth/login` | none | `{email, password}` | `200 {access_token, token_type, expires_in}` |
| GET | `/users/me` | user | none | `200 {id, name, email, role, age, gender, height_cm, weight_kg}` |
| PUT | `/users/me` | user | `{age?, gender?, height_cm?, weight_kg?, name?}` | `200` updated profile |
| POST | `/predict` | user | `{duration, heart_rate, body_temp, gender?, age?, height?, weight?}` | `200 {workout_id, predicted_calories, intensity, model_version, extrapolated, warnings}` |
| GET | `/workouts` | user | `page, page_size` | `200` paginated list |
| GET | `/workouts/summary` | user | none | `200 {week_total, avg_per_workout, count}` |
| DELETE | `/workouts/{id}` | user | none | `204` |
| GET | `/forecast/weekly` | user | none | `200 {method, weekly_total, daily:[7 numbers]}` |
| POST | `/sessions/start` | user | `{body_temp?}` | `201 {session_id, started_at}` |
| WS | `/sessions/{id}/stream` | user (query token) | see Section 7.4 | messages |
| POST | `/sessions/{id}/readings` | user | `{heart_rate, interval_sec?}` | `200` update object (polling fallback) |
| POST | `/sessions/{id}/end` | user | none | `200` summary |
| POST | `/admin/upload-data` | admin | multipart `file` | `201 {dataset_id, rows, status, message}` |
| POST | `/admin/retrain` | admin | `{dataset_id?}` | `202 {job_id}` |
| GET | `/admin/retrain/{job_id}` | admin | none | `200 {status, message, activated, model_version_id}` |
| GET | `/admin/models` | admin | none | `200 [ {id, algorithm, mae, rmse, r2, clf_accuracy, is_active, candidates, created_at} ]` |
| POST | `/admin/models/{id}/activate` | admin | none | `200` (rollback) |
| GET | `/health` | none | none | `200 {status:"ok", active_model_version}` |

Validation ranges come from `ml/config.py` (one place), so the schemas, the SRS table, and the frontend hints stay consistent.

---

## 9. Sequence Diagrams

### 9.1 Predict a Workout

```
Client        Router(/predict)   Security     PredictionSvc    Registry     DB
  | POST /predict |                 |               |             |         |
  |-------------->|  verify JWT --->|               |             |         |
  |               |<-- user --------|               |             |         |
  |               |-- validate schema (422 on fail) |             |         |
  |               |---------------------------> predict()         |         |
  |               |                             |-- active() ---->|         |
  |               |                             |<-- bundle ------|         |
  |               |                             | build_features, scale,    |
  |               |                             | regress + classify,       |
  |               |                             | range check               |
  |               |<----------- result ---------|             |         |
  |               |-- save workout ------------------------------------->|
  |<-- 200 {kcal, intensity, version, warnings}                |         |
```

### 9.2 Live Session

```
Client                 WS Handler          SessionSvc        Registry      DB
  | POST /sessions/start |                       |                |         |
  |--------------------------------------------> create session --------->|
  |<-- 201 {session_id}                            |                |         |
  | WS connect ?token=... |                        |                |         |
  |---------------------->| auth + ownership check |                |         |
  | {reading: hr=110}     |                        |                |         |
  |---------------------->| add_reading() -------->| update sums    |         |
  |                       |                        | predict cumulative --->|
  |                       |                        | store reading -------->|
  |<-- {update: kcal=6.2} |<-----------------------|                |         |
  |        ... repeats ...                                                     |
  | {end}                 |                        |                |         |
  |---------------------->| finish() ------------->| final calc, save workout->|
  |<-- {summary} + close  |                        |                |         |
```

### 9.3 Admin Retraining

```
Admin       Router(/admin)   AdminSvc     Background task     Registry     DB
  | upload CSV |               |                |                |          |
  |----------->| validate ---->| save + datasets row ------------------------>|
  |<-- 201     |               |                |                |          |
  | POST /admin/retrain        |                |                |          |
  |----------->| create job -->|--------------------------------------------->|
  |<-- 202 {job_id}            | start ------->| train 4 regressors + clf     |
  |                            |               | evaluate on frozen hold-out  |
  |                            |               | save bundle v{n}, insert row |
  |                            |               | try_activate() --------------->|
  |                            |               |     better? yes -> swap --->|  |
  |                            |               |     better? no  -> keep old    |
  |                            |               | update job (status, message) ->|
  | GET /admin/retrain/{id} -->| status, activated, metrics                    |
```

---

## 10. Frontend Design

The frontend is deliberately simple: static pages that call the API with `fetch`. Total effort target is about 2 days.

| Page | Purpose | API calls | Main UI parts |
|---|---|---|---|
| `login.html` | Register / login | `/auth/register`, `/auth/login` | Two forms with tabs, error alerts |
| `predict.html` | Make a prediction | `/users/me`, `/predict` | Form pre-filled from profile, result card (calories, intensity badge, warnings) |
| `dashboard.html` | History and forecast | `/workouts`, `/workouts/summary`, `/forecast/weekly` | History table with pagination, line chart of calories over time, 7-day forecast bar chart, "demo data" tag for seeded rows |
| `live.html` | Live session | `/sessions/start`, WebSocket, `/sessions/{id}/end` | Start/stop buttons, big running-calories counter, heart-rate chart, final summary card |
| `admin.html` | Data and models | `/admin/upload-data`, `/admin/retrain`, `/admin/retrain/{id}`, `/admin/models` | Upload form, retrain button with progress status, model-versions table, four-model comparison chart |

**JavaScript modules**
- `api.js`: a `request(path, options)` wrapper that adds the token, parses the error envelope, and redirects to `login.html` on `401`.
- `auth.js`: stores the token (localStorage for the prototype), decodes the role to show or hide the Admin link, and provides logout.
- One small script per page.

**Frontend rules**
- Show validation hints from the same ranges as the backend, but never trust them (the server always validates).
- Show a visible warning banner when a result has `extrapolated: true`.
- Demo helper: `simulate_stream.py` sends readings with a large `interval_sec` (for example 30) so a 10-minute workout can be shown in a few seconds.

---

## 11. Security Design

| Threat | Control |
|---|---|
| Stolen or guessed passwords | bcrypt hashing with salt; minimum password length; generic login error message |
| Token misuse | Short-lived JWT (60 min), signature check, expiry check, secret in environment variable |
| Access to other users' data | Every query filters by the authenticated `user_id`; `404` instead of `403` for someone else's record |
| Privilege escalation | Admin role can only be created by a server-side script; `require_admin` on all `/admin/*` routes |
| SQL injection | SQLAlchemy ORM with parameter binding; no string-built SQL |
| Malicious uploads | CSV only, size limit, uuid file names, parsed with pandas only, never executed |
| Unsafe model loading | Model files (`joblib`) are produced only by the server itself; users and admins upload CSV only, never model files |
| XSS | Frontend inserts server text with `textContent`, not `innerHTML` |
| Token in WebSocket URL is logged | Accepted for a prototype; mention it as a limitation (a production system would use a first-message auth or short-lived ticket) |
| Brute-force login | Optional: simple rate limit (for example with `slowapi`), listed as an improvement |
| Secret leakage | `.env` is in `.gitignore`; `.env.example` is committed instead |

---

## 12. Configuration, Errors, and Logging

**Environment variables (`.env.example`)**
```
DATABASE_URL=sqlite:///./caloriecast.db
JWT_SECRET=change-me
JWT_EXPIRE_MINUTES=60
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me-too
MAX_UPLOAD_MB=10
ARTIFACT_DIR=ml/artifacts
```

**Error handling**
- Custom exception classes (`Unauthorized`, `Forbidden`, `NotFound`, `Conflict`, `BadRequest`) are mapped to the error envelope by handlers in `errors.py`.
- Pydantic validation errors are converted to the same envelope with `422`.
- Unhandled exceptions return `500` with a generic message, and the stack trace goes only to the log.

**Logging**
- Use Python `logging` with a consistent format (timestamp, level, module, message) to console and a rotating file.
- Log: startup and active model version, each retrain job with its metrics, activation decisions, auth failures (without passwords or tokens), and unexpected exceptions.
- Never log passwords, tokens, or full request bodies.

---

## 13. Testing Strategy

| Level | What | Tools |
|---|---|---|
| Unit: ML | `build_features` order and encoding; range check; thresholds; forecast EMA math; monotonic cumulative calories | pytest |
| Unit: services | Prediction with a tiny fixture model; workout filtering by user | pytest |
| API integration | Full requests against the app with an in-memory SQLite database and dependency override | FastAPI TestClient |
| WebSocket | Connect, send readings, receive updates, end | TestClient websocket support |
| Manual / demo | Swagger UI walk-through and the 7-step demo script | Browser |

**Mapping to SRS test cases**

| Test file | Covers |
|---|---|
| `test_auth.py` | TC-1, TC-2, TC-3, TC-4, TC-11 |
| `test_predict.py` | TC-5, TC-6 |
| `test_workouts.py` | TC-7 |
| `test_forecast.py` | TC-8 |
| `test_sessions.py` | TC-9, TC-10 |
| `test_admin.py` | TC-12, TC-13, TC-14 |
| `test_ml.py` | ML-1 to ML-8 checks (shapes, determinism with fixed seed, artifact files exist) |

**Test setup tips:** create a tiny model bundle in a fixture (train on 200 rows) so tests do not depend on the full training run; create `user` and `admin` fixtures that return ready tokens.

---

## 14. Deployment and Operations

### 14.1 Local Run (primary demo mode)
```
python -m venv venv
venv\Scripts\activate            # Windows  (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # then edit values
python scripts/bootstrap_train.py     # trains, saves v1, activates it
python scripts/create_admin.py
python scripts/seed_demo_data.py
uvicorn app.main:app --reload
```
Open `http://127.0.0.1:8000/` for the app and `http://127.0.0.1:8000/docs` for the API docs.

### 14.2 Optional Online Deployment (Render or PythonAnywhere)
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- **Caveat:** free tiers often have a temporary disk, so the SQLite file and model artifacts may reset on restart. Mitigation: run the bootstrap (train, admin, seed) automatically on startup if no active model exists, or commit the `v1` bundle to the repository.
- Confirm that the host supports WebSockets; if not, switch the frontend to the polling fallback.
- Keep a **local copy and a recorded demo video** as a backup for the presentation.

### 14.3 Backup and Recovery
- Artifacts are files, so a full copy of `ml/artifacts/` plus the database file is a complete backup.
- If the active model fails to load at startup, fall back to the newest bundle that loads, and log it.

---

## 15. Traceability and Deviations from the SRS

### 15.1 Design-to-Requirement Mapping

| Design element | Requirements covered |
|---|---|
| `security.py`, `auth_service`, JWT and bcrypt | FR-1 to FR-8, NFR-4 to NFR-9 |
| `prediction_service`, `ml/features.py`, registry | FR-9 to FR-14, ML-1 to ML-5 |
| Intensity classifier and thresholds | FR-12, ML-6, ML-7 |
| `workout_service` | FR-15 to FR-18 |
| `forecast_service` | FR-19 to FR-22, ML-10 |
| `session_service`, WebSocket handler | FR-23 to FR-28, ML-9 |
| `admin_service`, `train.py`, `training_jobs`, `datasets` | FR-29 to FR-36, ML-8, NFR-11, NFR-12 |
| Frontend pages | FR-37, NFR-13 to NFR-15 |
| Error envelope, logging, tests | NFR-10, NFR-16 to NFR-18 |
| Config via environment | NFR-9, NFR-19, NFR-20 |

### 15.2 Refinements and Additions to the SRS
These small changes make the design work properly. Update the SRS to match, or mention them as "design refinements" in your report.

1. **`model_versions` stores a bundle**, not a single algorithm, and gains columns `clf_accuracy`, `clf_f1`, `candidates_json`, `training_job_id`, and `artifact_dir`.
2. **Two new tables:** `datasets` (uploaded files) and `training_jobs` (background retraining).
3. **Two new columns:** `workouts.source` (`manual`, `session`, `seed`) and `workouts.extrapolated`; `sessions` also stores running aggregates.
4. **New endpoints:** `GET /admin/retrain/{job_id}`, `POST /sessions/{id}/readings` (polling fallback), `GET /workouts/summary`, `POST /admin/models/{id}/activate`, `GET /health`.
5. **Frozen hold-out set** (decision D5): retraining evaluates on a permanent hold-out, and uploaded data only adds to training. This makes FR-34's "better than the active model" comparison fair.
6. **Extrapolation warning:** because the API accepts wider ranges than the dataset covers, predictions outside the training range are flagged instead of rejected.
7. **Retrain is asynchronous** (`202 Accepted` and job polling) instead of a blocking call.

---

## 16. Implementation Order and Definition of Done

| Phase | Days | Build | Done when |
|---|---|---|---|
| 1 | 1 | Repo, folders, `config.py`, `.env.example`, empty FastAPI app with `/health` | `/health` and `/docs` load |
| 2 | 2-6 | EDA notebook, `preprocess.py`, `features.py`, `train.py`, frozen hold-out, model comparison, classifier, temp model, first bundle | `python scripts/bootstrap_train.py` creates `v1` and metrics are printed |
| 3 | 7-11 | `models.py`, `database.py`, `security.py`, auth, users, `/predict`, workouts | TC-1 to TC-7 pass |
| 4 | 12-15 | `forecast_service`, seed script, `session_service`, WebSocket and polling fallback, `simulate_stream.py` | TC-8 to TC-10 pass; live demo updates smoothly |
| 5 | 16-17 | Upload validation, background retraining, activation logic, model list | TC-11 to TC-14 pass |
| 6 | 18-19 | Five frontend pages | Full demo runs in the browser |
| 7 | 20-21 | Tests cleanup, README, report, diagrams, slides, backup video | 7-step demo runs twice without errors |

**Priority if time runs short:** keep everything in Phases 1 to 5 and the Predict and Dashboard pages. Cut the Ridge lag model, CSV export, clustering, rollback, and online deployment first.

---

## 17. Open Decisions to Confirm

| Question | Suggested default |
|---|---|
| WebSocket or polling for the demo? | Try WebSocket first; polling fallback is already designed |
| Keep ANN in the final bundle if it does not win? | Yes, it stays in the comparison table (it still satisfies the ANN requirement) |
| SQLite or MySQL for the final demo? | SQLite; mention MySQL/PostgreSQL as a configuration change |
| Deploy online? | Optional; local demo plus backup video is enough |
| Report format from the university | Confirm with your guide before writing the report |
