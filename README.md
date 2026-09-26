# CalorieCast — ML/DL Calorie Burnt Forecaster

CalorieCast is a full-stack, backend-focused machine learning and deep learning application designed to forecast exercise calorie expenditure, classify workout intensity, stream real-time workout telemetry, and automate model retraining.

---

## 🌟 Key Features

1. **Multi-Model Regression Engine**
   - Implements four regressor algorithms: **Linear Regression**, **Random Forest**, **K-Nearest Neighbors (KNN with GridSearchCV)**, and **Artificial Neural Network (ANN / MLP Regressor)**.
   - Evaluates models on a **frozen 20% holdout dataset** using Root Mean Squared Error (RMSE), Mean Absolute Error (MAE), and $R^2$.
   - Predicts total calories based on 7 features: `gender`, `age`, `height`, `weight`, `duration`, `heart_rate`, and `body_temp`.

2. **Physiological Intensity Classifier**
   - Automatically categorizes exercises into **Low**, **Moderate**, or **High** intensity using dynamically learned percentile thresholds without target leakage.

3. **Live Simulated Telemetry Tracker**
   - Full duplex **WebSocket streaming** (`/sessions/{id}/stream`) with HTTP polling fallback (`/sessions/{id}/readings`).
   - Guarantees **monotonic cumulative calorie accumulation** and estimates dynamic body temperature if not provided.

4. **7-Day ISO-Week Forecasting**
   - Computes 7-day projected calorie burn using **Exponential Moving Average (EMA, $\alpha=0.5$)** across completed ISO weeks with weekday historical weighting.
   - Graceful fallback for new users without sufficient history.

5. **Production MLOps Retraining Pipeline**
   - Admin CSV upload with schema validation, range checks, and type enforcement.
   - Asynchronous background retraining (`202 Accepted`) with real-time job status tracking.
   - Automated model promotion **only if candidate RMSE outperforms active model**. One-click model rollback.

---

## 🏗️ Architecture

```
                   +------------------------+
                   |  HTML / CSS / JS UI    |
                   +-----------+------------+
                               |
                               v
                     +--------------------+
                     |  FastAPI (Uvicorn) |
                     +---------+----------+
                               |
            +------------------+------------------+
            |                                     |
            v                                     v
+-----------------------+              +---------------------+
| Routers & Security    |              | Background Workers  |
| - /auth, /users       |              | - Model Retraining  |
| - /predict, /workouts |              | - Stale Session Cln |
| - /sessions, /admin   |              +----------+----------+
+-----------+-----------+                         |
            |                                     |
            v                                     v
+-----------------------+              +---------------------+
| Domain Services Layer |              | Machine Learning    |
| - PredictionService   |              | - StandardScaler    |
| - SessionService      | <----------> | - ModelRegistry     |
| - ForecastService     |              | - Bundles (v1, v2)  |
| - AdminService        |              +---------------------+
+-----------+-----------+
            |
            v
+-----------------------+
|  SQLAlchemy 2.0 ORM   |
|     (SQLite DB)       |
+-----------------------+
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites & Environment Setup

Using Python (e.g. Anaconda / Virtualenv):

```bash
# Clone or navigate to the directory
cd D:\Calorie

# Install required dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env` (already created with defaults):

```bash
copy .env.example .env
```

### 3. Bootstrap & Seed

Run the setup scripts in sequence:

```bash
# 1. Train base models, pick best on frozen holdout, and activate v1
python scripts/bootstrap_train.py

# 2. Create the default administrator account
python scripts/create_admin.py

# 3. Seed demo users with 8 weeks of workout history
python scripts/seed_demo_data.py
```

### 4. Run the Web Application

Start the FastAPI application:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **Web Application:** [http://127.0.0.1:8000/static/index.html](http://127.0.0.1:8000/static/index.html)
- **Interactive API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 5. Default Credentials

- **Admin Portal:** `admin@caloriecast.local` / `AdminPassword123!`
- **Demo User:** `alex@example.com` / `Password123!`

---

## 🧪 Testing

Execute the test suite covering TC-1 through TC-14:

```bash
pytest -v
```

---

## 📜 Project Structure

```
d:\Calorie\
├── app/
│   ├── main.py                 # FastAPI application factory and lifespan
│   ├── config.py               # Settings and environment configuration
│   ├── database.py             # SQLAlchemy session and engine setup
│   ├── models.py               # ORM database models
│   ├── schemas.py              # Pydantic request/response models
│   ├── security.py             # JWT token handling & bcrypt authentication
│   ├── errors.py               # Error envelope and exception handlers
│   ├── routers/                # API route controllers
│   └── services/               # Core business and domain logic
├── ml/
│   ├── config.py               # ML hyperparameters & feature definitions
│   ├── features.py             # Feature extraction and encoding
│   ├── preprocess.py           # Data cleaning & frozen holdout splitting
│   ├── evaluate.py             # Regression & classification metrics
│   ├── train.py                # Model bundle training and selection
│   ├── registry.py             # In-memory model registry & hot-swapping
│   └── artifacts/              # Persisted model bundles (v1, v2...)
├── frontend/                   # Static web pages, styles, and scripts
├── scripts/                    # Bootstrap, admin creation, seeding, stream simulation
├── tests/                      # Pytest acceptance and integration suite
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```
