# CalorieCast: Software Requirements Specification (SRS)

*Structure follows the IEEE 830 / ISO 29148 style.*

| Field | Details |
|---|---|
| **Project** | CalorieCast: Real-Time Calories Burnt Prediction and Forecasting System |
| **Document version** | 1.0 |
| **Date** | 24 September 2026 |
| **Prepared by** | [Your Name], BCA 4th Semester |
| **Institution** | [College / University Name] |
| **Guide** | [Guide Name] |

## Revision History

| Version | Date | Description | Author |
|---|---|---|---|
| 1.0 | 24 Sep 2026 | Initial SRS | [Your Name] |

---

## 1. Introduction

### 1.1 Purpose
This document specifies the software requirements of CalorieCast. It describes what the system must do, the constraints it works under, and how each requirement can be verified. It is intended for the developer, the project guide, and evaluators.

### 1.2 Scope
CalorieCast is a web-based system with a machine learning backend. It will:
- Predict calories burnt for a workout using trained ML/DL models.
- Classify workout intensity.
- Track a live workout session with running calorie totals.
- Store workout history for each user.
- Forecast weekly calorie burn from the user's history.
- Let an admin upload data, retrain, and manage model versions.

It will not integrate with real wearables, provide medical advice, or track food intake.

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Meaning |
|---|---|
| API | Application Programming Interface |
| REST | Representational State Transfer |
| JWT | JSON Web Token, used for authentication |
| ML / DL | Machine Learning / Deep Learning |
| ANN | Artificial Neural Network |
| KNN | K-Nearest Neighbours |
| MAE | Mean Absolute Error |
| RMSE | Root Mean Squared Error |
| R² | Coefficient of determination |
| kcal | Kilocalorie |
| CRUD | Create, Read, Update, Delete |
| WebSocket | Two-way real-time communication protocol over a single connection |

### 1.4 References
- CalorieCast Product Requirements Document (PRD), v1.0
- Kaggle "Calories Burnt Prediction" dataset (exercise.csv and calories.csv)
- FastAPI, SQLAlchemy, scikit-learn, and TensorFlow/Keras official documentation
- IEEE Std 830-1998, Recommended Practice for Software Requirements Specifications

### 1.5 Document Overview
Section 2 gives the overall description. Section 3 lists specific requirements (functional, interface, data, non-functional). Section 4 covers system models. Section 5 covers verification and traceability.

---

## 2. Overall Description

### 2.1 Product Perspective
CalorieCast is a new, self-contained system. It has a browser-based frontend, a Python backend exposing a REST API and a WebSocket endpoint, a relational database, and a set of saved ML model files. It does not depend on any external paid service.

```
Browser (HTML / Bootstrap / Chart.js)
        |
  REST API + WebSocket (FastAPI)
        |
 +------+----------------+---------------+
 Auth   Prediction       Session         Admin
 module service          tracker         (retrain)
        |                   |               |
   ML models + scaler       |          ML pipeline
   (.pkl / .h5)             |          (train, evaluate)
        +---------+---------+
              Database (SQLite)
```

### 2.2 Product Functions (summary)
1. User registration, login, and role-based access.
2. Calorie prediction and intensity classification.
3. Workout history management.
4. Weekly calorie forecast.
5. Real-time session tracking.
6. Admin data upload, retraining, and model version management.
7. Input validation, error handling, and API documentation.

### 2.3 User Classes and Characteristics

| User class | Characteristics |
|---|---|
| **Registered User** | Non-technical; uses the web interface to predict, track, and view history |
| **Administrator** | Basic technical knowledge; manages data and models |
| **Developer / Evaluator** | Uses the API documentation and tests endpoints directly |

### 2.4 Operating Environment
- **Server:** Python 3.10 or newer on Windows, Linux, or macOS; or a free hosting service such as Render or PythonAnywhere.
- **Client:** any modern browser (Chrome, Edge, Firefox) on desktop or mobile.
- **Database:** SQLite (default), with the option to move to MySQL or PostgreSQL.
- **Minimum hardware:** 4 GB RAM, dual-core CPU. No GPU is required for inference.

### 2.5 Design and Implementation Constraints
- Single developer and approximately three weeks.
- Only free and open-source tools.
- Passwords must be stored as hashes, never as plain text.
- The dataset has no time dimension, so forecasting depends on history logged inside the application.
- Heart-rate streams are simulated for demonstration.

### 2.6 Assumptions and Dependencies
- The Kaggle dataset remains available and is representative enough for a prototype.
- Users enter honest and reasonably accurate inputs.
- Python libraries listed in `requirements.txt` install without problems.
- The evaluator's machine or the hosting service supports WebSockets, or the polling fallback is used.

---

## 3. Specific Requirements

### 3.1 Functional Requirements

Priority key: **M** = Must, **S** = Should, **C** = Could.

#### 3.1.1 Authentication and Authorization

| ID | Requirement | Priority |
|---|---|---|
| FR-1 | The system shall allow a new user to register with name, email, and password. | M |
| FR-2 | The system shall reject registration if the email already exists or the input is invalid. | M |
| FR-3 | The system shall store passwords only as salted hashes (bcrypt). | M |
| FR-4 | The system shall allow login with email and password and return an access token (JWT). | M |
| FR-5 | The system shall reject expired or invalid tokens on protected endpoints. | M |
| FR-6 | The system shall support two roles: `user` and `admin`. | M |
| FR-7 | The system shall restrict admin endpoints to users with the `admin` role. | M |
| FR-8 | The system shall let a user save and update profile details (age, gender, height, weight). | M |

#### 3.1.2 Calorie Prediction and Intensity Classification

| ID | Requirement | Priority |
|---|---|---|
| FR-9 | The system shall accept gender, age, height, weight, duration, heart rate, and body temperature and return predicted calories burnt. | M |
| FR-10 | The system shall validate all inputs against allowed ranges (Section 3.3.1) before prediction. | M |
| FR-11 | The system shall apply the same scaling used in training before prediction. | M |
| FR-12 | The system shall classify each workout as low, moderate, or high intensity. | M |
| FR-13 | The system shall use only the model version marked active. | M |
| FR-14 | The system shall save each prediction with the inputs, result, intensity, and timestamp. | M |

#### 3.1.3 Workout History

| ID | Requirement | Priority |
|---|---|---|
| FR-15 | The system shall return a user's own workout history, newest first, with pagination. | M |
| FR-16 | The system shall never return another user's workout data to a regular user. | M |
| FR-17 | The system shall let a user delete their own workout record. | S |
| FR-18 | The system shall provide summary values (total calories this week, average per workout). | S |

#### 3.1.4 Weekly Forecast

| ID | Requirement | Priority |
|---|---|---|
| FR-19 | The system shall return a 7-day calorie burn forecast for the logged-in user. | M |
| FR-20 | The system shall compute the forecast from the user's past weekly totals using a moving average or a regression on lag features when sufficient history exists (for example 3 or more weeks). | M |
| FR-21 | The system shall use a fallback estimate based on the ML model and the user's usual routine when history is insufficient. | M |
| FR-22 | The system shall indicate which method (history-based or fallback) produced the forecast. | S |

#### 3.1.5 Real-Time Session Tracking

| ID | Requirement | Priority |
|---|---|---|
| FR-23 | The system shall let a user start a workout session and create a session record. | M |
| FR-24 | The system shall accept heart-rate readings during an active session over a WebSocket (or by polling as fallback). | M |
| FR-25 | The system shall calculate and return cumulative calories after each reading. | M |
| FR-26 | The system shall store every reading with its timestamp and cumulative calories. | M |
| FR-27 | The system shall let the user end the session and save a summary (duration, average heart rate, total calories, intensity). | M |
| FR-28 | The system shall reject readings for sessions that are ended or do not belong to the user. | M |

#### 3.1.6 Admin: Data and Model Management

| ID | Requirement | Priority |
|---|---|---|
| FR-29 | The system shall let an admin upload a CSV dataset. | M |
| FR-30 | The system shall validate the uploaded file (required columns, data types, missing values, ranges) and reject invalid files with a clear message. | M |
| FR-31 | The system shall retrain the candidate models (Linear Regression, Random Forest, KNN, ANN) on admin request. | M |
| FR-32 | The system shall evaluate models on a held-out test set and record MAE, RMSE, and R². | M |
| FR-33 | The system shall save each trained model as a new version in `model_versions`. | M |
| FR-34 | The system shall activate a new model only if it performs better than the currently active model on the same test data. | M |
| FR-35 | The system shall let an admin view all model versions and their metrics. | M |
| FR-36 | The system shall allow an admin to roll back to a previous model version. | C |

#### 3.1.7 Dashboard and Reporting

| ID | Requirement | Priority |
|---|---|---|
| FR-37 | The frontend shall show a history table and a chart of calories over time. | S |
| FR-38 | The system shall let a user export their history as CSV. | C |
| FR-39 | The system shall group users into activity profiles using K-Means clustering. | C |

### 3.2 External Interface Requirements

#### 3.2.1 User Interface
- Simple responsive pages built with HTML and Bootstrap: Login/Register, Predict, Dashboard, Live Session, and Admin.
- Forms show inline validation messages.
- Results appear as clearly labelled cards (calories, intensity).
- Charts use Chart.js.

#### 3.2.2 Software Interfaces

| Interface | Description |
|---|---|
| REST API | JSON over HTTP; documented automatically at `/docs` (Swagger UI) |
| WebSocket | `/sessions/{id}/stream` for real-time readings and responses |
| Database | SQLAlchemy ORM to SQLite (or MySQL/PostgreSQL) |
| ML runtime | scikit-learn models loaded with joblib; Keras model loaded from `.h5` or `.keras` |

#### 3.2.3 Hardware Interfaces
None required. Heart-rate input comes from a form or a simulated stream.

#### 3.2.4 Communication Interfaces
- HTTP/HTTPS for REST calls.
- WebSocket for live session updates.
- All protected requests carry a bearer token in the `Authorization` header.

### 3.3 Data Requirements

#### 3.3.1 Input Validation Ranges (defaults, configurable)

| Field | Allowed range |
|---|---|
| Age | 10 to 100 years |
| Height | 100 to 230 cm |
| Weight | 30 to 200 kg |
| Duration | 1 to 300 minutes |
| Heart rate | 40 to 220 bpm |
| Body temperature | 35 to 42 °C |
| Gender | `male` or `female` |

#### 3.3.2 Database Schema

**users**

| Column | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| name | String | Required |
| email | String | Unique, required |
| password_hash | String | bcrypt hash |
| role | String | `user` or `admin` |
| age, gender, height, weight | Numeric / String | Profile values |
| created_at | DateTime | |

**workouts**

| Column | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| user_id | Integer | Foreign key to users |
| duration, heart_rate, body_temp | Numeric | Inputs |
| predicted_calories | Float | Output |
| intensity | String | low / moderate / high |
| model_version_id | Integer | Foreign key to model_versions |
| created_at | DateTime | |

**sessions**

| Column | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| user_id | Integer | Foreign key |
| started_at, ended_at | DateTime | |
| total_calories | Float | Filled at end |
| status | String | active / ended |

**readings**

| Column | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| session_id | Integer | Foreign key |
| heart_rate | Integer | |
| timestamp | DateTime | |
| cumulative_calories | Float | |

**model_versions**

| Column | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| name | String | Algorithm name |
| file_path | String | Saved artifact location |
| mae, rmse, r2 | Float | Evaluation metrics |
| is_active | Boolean | Only one active at a time |
| created_at | DateTime | |

#### 3.3.3 Relationships
- One user has many workouts and many sessions.
- One session has many readings.
- One model version can be referenced by many workouts.

### 3.4 API Specification (summary)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | None | Create account |
| POST | `/auth/login` | None | Return access token |
| GET / PUT | `/users/me` | User | View or update profile |
| POST | `/predict` | User | Predict calories and intensity |
| GET | `/workouts` | User | List own workout history |
| DELETE | `/workouts/{id}` | User | Delete own workout |
| GET | `/forecast/weekly` | User | 7-day forecast |
| POST | `/sessions/start` | User | Start a live session |
| WS | `/sessions/{id}/stream` | User | Send readings, receive cumulative calories |
| POST | `/sessions/{id}/end` | User | End session and save summary |
| POST | `/admin/upload-data` | Admin | Upload and validate dataset |
| POST | `/admin/retrain` | Admin | Retrain and evaluate models |
| GET | `/admin/models` | Admin | List model versions and metrics |

**Example: POST /predict**

Request:
```json
{
  "gender": "male",
  "age": 25,
  "height": 175,
  "weight": 70,
  "duration": 30,
  "heart_rate": 110,
  "body_temp": 40.0
}
```

Response:
```json
{
  "predicted_calories": 145.3,
  "intensity": "moderate",
  "model_version": 3
}
```

Standard error responses: `400` invalid input, `401` unauthenticated, `403` forbidden, `404` not found, `422` validation error, `500` server error.

### 3.5 Machine Learning Requirements

| ID | Requirement |
|---|---|
| ML-1 | The pipeline shall clean data (duplicates, missing values, outliers) and encode gender numerically. |
| ML-2 | The pipeline shall split data into training and test sets (for example 80/20) with a fixed random seed. |
| ML-3 | Numeric features shall be scaled, and the fitted scaler shall be saved and reused at prediction time. |
| ML-4 | The pipeline shall train and compare Linear Regression, Random Forest, KNN Regressor, and an ANN. |
| ML-5 | Regression models shall be evaluated using MAE, RMSE, and R². |
| ML-6 | Intensity labels shall be derived from calories per minute using thresholds computed from the training data. |
| ML-7 | The intensity classifier shall be evaluated using accuracy, precision, recall, F1, and a confusion matrix. |
| ML-8 | Training shall run with a single command (`python ml/train.py`) and save the best model and scaler to `ml/artifacts/`. |
| ML-9 | The live session calculation shall use the active model with the session's running average heart rate and elapsed time, and the method shall be documented. |
| ML-10 | The forecast shall use a moving average or a regression on lag features, and its error on held-out weeks shall be reported when enough seeded history exists. |

### 3.6 Non-Functional Requirements

#### 3.6.1 Performance
- NFR-1: A prediction request shall complete in under 500 ms on a standard laptop (target).
- NFR-2: A live-session reading shall be processed and answered in under 2 seconds (target).
- NFR-3: The system shall support at least 10 simultaneous users during the demo.

#### 3.6.2 Security
- NFR-4: Passwords shall be hashed with bcrypt and never logged or returned.
- NFR-5: Protected endpoints shall require a valid JWT.
- NFR-6: The system shall enforce role-based access on all admin endpoints.
- NFR-7: Database access shall use parameterized queries through the ORM to prevent SQL injection.
- NFR-8: Uploaded files shall be size-limited and type-checked (CSV only).
- NFR-9: Secrets (JWT key, database URL) shall be kept in environment variables, not in source code.

#### 3.6.3 Reliability and Availability
- NFR-10: The system shall return clear error messages and shall not crash on invalid input.
- NFR-11: If a new model fails to load, the system shall keep using the previous active model.
- NFR-12: Failed retraining shall not change the active model.

#### 3.6.4 Usability
- NFR-13: A first-time user shall be able to register and get a prediction in under 2 minutes.
- NFR-14: All forms shall show understandable validation messages.
- NFR-15: The interface shall work on both desktop and mobile screens.

#### 3.6.5 Maintainability
- NFR-16: Code shall follow the modular folder structure (routers, services, models, schemas, ml).
- NFR-17: The project shall include a README with setup and run instructions and a `requirements.txt`.
- NFR-18: Core logic shall be covered by automated tests (pytest).

#### 3.6.6 Portability
- NFR-19: The system shall run on Windows, Linux, and macOS with Python 3.10 or newer.
- NFR-20: Switching from SQLite to MySQL/PostgreSQL shall require only a configuration change.

#### 3.6.7 Accuracy (model quality targets)
- NFR-21: Regression R² of 0.95 or higher on the held-out test set (target, to be validated).
- NFR-22: Intensity classifier accuracy of 90% or higher (target, to be validated).

---

## 4. System Models

### 4.1 Use Cases

| ID | Use case | Actor | Main flow |
|---|---|---|---|
| UC-1 | Register / Login | User, Admin | Enter credentials, system validates, returns token |
| UC-2 | Predict calories | User | Enter workout data, system validates, predicts, saves, and displays result |
| UC-3 | View history | User | Request history, system returns user's records |
| UC-4 | View weekly forecast | User | Request forecast, system computes and returns 7-day projection |
| UC-5 | Run live session | User | Start session, stream readings, view running calories, end session |
| UC-6 | Upload dataset | Admin | Upload CSV, system validates and stores |
| UC-7 | Retrain model | Admin | Trigger retraining, system evaluates, versions, and conditionally activates |
| UC-8 | View model versions | Admin | Request list, system shows metrics and active flag |

**Alternate flows (examples)**
- UC-2: If any input is outside its allowed range, the system returns a validation error and does not save anything.
- UC-5: If the connection drops, the user can resume by reconnecting to the same active session, or end it.
- UC-7: If the new model is not better than the active one, it is saved as inactive and the active model does not change.

### 4.2 Entity Relationship Overview

```
users 1 ---- * workouts * ---- 1 model_versions
users 1 ---- * sessions 1 ---- * readings
```

### 4.3 Data Flow (Prediction)

1. Client sends inputs with a token to `POST /predict`.
2. API validates the token and inputs.
3. Service loads the active model and scaler.
4. Inputs are scaled and passed to the model.
5. Predicted calories and intensity are computed.
6. Result is saved in `workouts` and returned to the client.

### 4.4 Deployment View
Single application server (FastAPI with Uvicorn) with the database file and model artifacts on the same machine for the prototype. The frontend is served as static files by the same server.

---

## 5. Verification and Traceability

### 5.1 Sample Acceptance Test Cases

| Test ID | Scenario | Input | Expected result | Covers |
|---|---|---|---|---|
| TC-1 | Register with valid data | Name, unique email, password | Account created, HTTP 201 | FR-1 |
| TC-2 | Register with duplicate email | Existing email | Error, no account created | FR-2 |
| TC-3 | Login with wrong password | Valid email, wrong password | HTTP 401 | FR-4 |
| TC-4 | Access history without token | No token | HTTP 401 | FR-5 |
| TC-5 | Valid prediction | Valid workout inputs | Calories and intensity returned, record saved | FR-9, FR-12, FR-14 |
| TC-6 | Invalid heart rate | Heart rate 400 | Validation error, nothing saved | FR-10 |
| TC-7 | View another user's data | User A requests user B's records | Not returned | FR-16 |
| TC-8 | Forecast with no history | New user | Fallback forecast returned and labelled | FR-21, FR-22 |
| TC-9 | Live session flow | Start, 10 readings, end | Cumulative calories rise; summary saved | FR-23 to FR-27 |
| TC-10 | Reading on ended session | Send reading after end | Rejected | FR-28 |
| TC-11 | Admin route as normal user | User calls `/admin/retrain` | HTTP 403 | FR-7 |
| TC-12 | Upload invalid CSV | Missing columns | Rejected with message | FR-30 |
| TC-13 | Retrain with better model | Valid new data | New version created and activated | FR-31 to FR-34 |
| TC-14 | Retrain with worse model | Poor data | Saved as inactive; active model unchanged | FR-34, NFR-12 |

### 5.2 Requirements Traceability Matrix (PRD to SRS)

| PRD feature | SRS requirements |
|---|---|
| F1 Auth and roles | FR-1 to FR-8, NFR-4 to NFR-6 |
| F2 Prediction | FR-9 to FR-11, FR-13, FR-14, ML-1 to ML-5 |
| F3 Intensity classification | FR-12, ML-6, ML-7 |
| F4 History | FR-15 to FR-18 |
| F5 Weekly forecast | FR-19 to FR-22, ML-10 |
| F6 Real-time session | FR-23 to FR-28, ML-9 |
| F7 Admin retraining | FR-29 to FR-36, ML-8 |
| F8 Input validation | FR-10, Section 3.3.1 |
| F9 API documentation | Section 3.4, Section 3.2.2 |
| F10 Dashboard | FR-37 |
| F11 Clustering | FR-39 |
| F12 Export | FR-38 |

---

## 6. Appendices

### Appendix A: Technology Stack
Python 3.10+, FastAPI, Uvicorn, SQLAlchemy, SQLite, pandas, NumPy, scikit-learn, TensorFlow/Keras, joblib, bcrypt, PyJWT, HTML, Bootstrap, Chart.js, pytest, Git/GitHub, Google Colab.

### Appendix B: Proposed Folder Structure

```
caloriecast/
├── app/
│   ├── main.py
│   ├── routers/        # auth.py, predict.py, sessions.py, admin.py
│   ├── services/       # prediction, forecast, intensity logic
│   ├── models.py
│   ├── schemas.py
│   └── database.py
├── ml/
│   ├── train.py
│   ├── preprocess.py
│   └── artifacts/
├── data/               # datasets and seed script
├── frontend/
├── tests/
├── requirements.txt
└── README.md
```

### Appendix C: Known Limitations
- The public dataset has no time dimension, so the weekly forecast is based on seeded and user-logged history and is a demonstration of the method, not a validated health forecast.
- Heart-rate streams are simulated; no real wearable is connected.
- Estimates are approximate and not medical advice.
