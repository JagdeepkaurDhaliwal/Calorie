# CalorieCast: Product Requirements Document (PRD)

| Field | Details |
|---|---|
| **Product name** | CalorieCast: Real-Time Calories Burnt Prediction and Forecasting System |
| **Document version** | 1.0 |
| **Date** | 24 September 2026 |
| **Author** | [Your Name], BCA 4th Semester |
| **Institution** | [College / University Name] |
| **Guide / Supervisor** | [Guide Name] |
| **Project type** | Final prototype project (Machine Learning / Deep Learning) |
| **Status** | Draft for review |

---

## 1. Overview

CalorieCast is a backend-focused web application that predicts the calories burnt during a workout using machine learning, tracks a workout session in real time, classifies workout intensity, and forecasts the user's calorie burn for the coming week from their logged history.

The product is a prototype. Its main goal is to demonstrate a complete, working ML/DL system: data pipeline, trained models, a secure REST API, a database, real-time session tracking, and an admin retraining workflow, with a simple frontend on top.

## 2. Problem Statement

Fitness apps and gym machines usually estimate calories burnt with fixed formulas. These formulas ignore individual differences, so the results are often inaccurate for a specific person. Users also cannot easily see how their calorie burn changes over time or what to expect next week.

**Core problem:** There is no simple, data-driven, personalized way for an individual to get an accurate calorie estimate for a workout, watch it update live during exercise, and see a forecast of their future activity.

## 3. Goals and Non-Goals

### 3.1 Goals

1. Predict calories burnt for a workout from personal and workout inputs using ML models.
2. Compare several models (Linear Regression, Random Forest, KNN, ANN) and use the best one in production.
3. Classify each workout as low, moderate, or high intensity.
4. Track a live workout session and show cumulative calories in real time.
5. Store workout history per user and forecast the next 7 days of calorie burn.
6. Let an admin upload new data, retrain models, and safely switch to a better model.
7. Provide a secure, documented REST API with a simple web frontend.

### 3.2 Non-Goals (out of scope for this prototype)

- Integration with real wearable devices (Fitbit, Apple Watch, etc.). Heart-rate streams are simulated.
- Mobile application (native Android/iOS).
- Medical-grade accuracy or health diagnosis.
- Diet, nutrition, or calorie intake tracking.
- Payment, subscriptions, or social features.
- Large-scale deployment and load handling.

## 4. Target Users

| Persona | Description | Main need |
|---|---|---|
| **Fitness Beginner (Primary)** | Adult who exercises a few times a week and wants to understand effort | Simple, accurate calorie estimate and weekly trend |
| **Regular Gym-goer** | Tracks workouts and wants more personalized numbers | Live session tracking, intensity feedback, history |
| **Admin / Data Manager** | Maintains the system and models | Upload data, retrain, compare model versions |
| **Evaluator / Examiner** | Reviews the project | Clear demo of ML, backend, and API quality |

## 5. User Stories

### Regular user
- As a user, I want to register and log in securely so that my data stays private.
- As a user, I want to enter my details and workout information to get a predicted calorie burn.
- As a user, I want to see whether my workout was low, moderate, or high intensity.
- As a user, I want to start a live session and watch calories burnt update in real time.
- As a user, I want to view my workout history and see it on a chart.
- As a user, I want a forecast of my calorie burn for the next week.

### Admin
- As an admin, I want to upload a new dataset so the model can learn from more data.
- As an admin, I want to retrain the model and see its accuracy metrics.
- As an admin, I want the new model to become active only if it performs better than the current one.
- As an admin, I want to see all model versions and their metrics.

## 6. Features and Priority (MoSCoW)

| ID | Feature | Priority |
|---|---|---|
| F1 | User registration and login with hashed passwords, user and admin roles | Must |
| F2 | Calorie prediction from user and workout inputs | Must |
| F3 | Intensity classification (low / moderate / high) | Must |
| F4 | Workout history storage and retrieval | Must |
| F5 | Weekly calorie forecast | Must |
| F6 | Real-time session tracking with cumulative calories | Must |
| F7 | Admin dataset upload, retraining, and model version tracking | Must |
| F8 | Input validation and clear error messages | Must |
| F9 | Auto-generated API documentation (Swagger/OpenAPI) | Must |
| F10 | Dashboard with history table and charts | Should |
| F11 | User activity clustering (K-Means profiles) | Could |
| F12 | Export report as CSV/PDF | Could |
| F13 | Online deployment | Could |
| F14 | CNN-based feature (for example exercise or food photo recognition) | Won't (this release) |

## 7. Key User Flows

**Flow 1: Predict a workout**
1. User logs in.
2. User opens the Predict page and enters duration, heart rate, and body temperature (profile values are pre-filled).
3. System validates the input, runs the model, and returns predicted calories and intensity.
4. Result is saved to the user's history.

**Flow 2: Live session**
1. User clicks Start Session.
2. Heart-rate readings arrive every few seconds (simulated stream for the demo).
3. System updates cumulative calories after each reading and pushes it to the screen.
4. User clicks End Session. A summary is saved to history.

**Flow 3: Weekly forecast**
1. User opens the Dashboard.
2. System reads the user's past weekly totals and computes a 7-day projection.
3. If the user has too little history, the system uses a fallback estimate based on the ML model and the user's usual routine.

**Flow 4: Admin retraining**
1. Admin uploads a new CSV.
2. System validates it, retrains the models, and evaluates them on a held-out test set.
3. System stores the metrics as a new model version and activates it only if it beats the current active model.

## 8. Functional Scope Summary

- **Authentication and authorization:** register, login, role-based access.
- **Prediction service:** loads the active model and scaler, predicts calories and intensity.
- **Forecast service:** weekly projection from history (moving average or lag-feature regression).
- **Session tracker:** real-time endpoint (WebSocket, or polling as fallback).
- **Admin module:** upload, retrain, compare, activate.
- **Data layer:** relational database with users, workouts, sessions, readings, and model versions.
- **Frontend:** simple pages (login, predict, dashboard, live session, admin).

## 9. Data and Model Requirements

- **Dataset:** Kaggle "Calories Burnt Prediction" (about 15,000 records with gender, age, height, weight, duration, heart rate, body temperature, calories).
- **Regression models compared:** Linear Regression, Random Forest, KNN Regressor, ANN (Keras).
- **Classification:** intensity label derived from calories per minute, using thresholds defined from the training data (for example the 33rd and 66th percentile), classified with a KNN or tree-based classifier.
- **Metrics:** MAE, RMSE, and R² for regression; accuracy, precision, recall, F1, and confusion matrix for classification.
- **Forecast data:** the dataset has no time dimension, so weekly forecasting uses workout history logged in the application database. A seed script generates sample history for demo users, and this limitation is stated in the project report.

## 10. Success Metrics

| Metric | Target |
|---|---|
| Regression R² on held-out test set | 0.95 or higher |
| Regression MAE | Low single-digit kcal (target: 5 kcal or less) |
| Intensity classifier accuracy | 90% or higher |
| Prediction API response time | Under 500 ms on a normal laptop |
| Live session update delay | Under 2 seconds per reading |
| Automated test pass rate | 100% of written tests |
| Demo completion | All 7 demo steps run without errors |

These are targets to be validated during development and reported honestly in the final report.

## 11. Assumptions and Constraints

**Assumptions**
- The Kaggle dataset is representative enough for a prototype.
- Users provide reasonably accurate heart rate and body temperature values.
- The demo runs on a local machine or a free hosting tier with an internet connection.

**Constraints**
- Team size: one student.
- Time: approximately 3 weeks.
- Budget: free tools and free hosting only.
- Tech limited to the student's current knowledge: Python, regression, classification, KNN, clustering, ANN, CNN.

## 12. Dependencies

- Python 3.10+ and libraries: FastAPI, SQLAlchemy, pandas, NumPy, scikit-learn, TensorFlow/Keras, joblib, bcrypt, PyJWT.
- Google Colab for model training and experiments.
- GitHub for version control.
- Kaggle for the dataset.

## 13. Risks and Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Not enough time for all features | High | Build Must features first; drop Could features |
| WebSocket implementation is difficult | Medium | Fall back to polling every 3-5 seconds |
| Model overfits or gives unrealistic values | Medium | Use train/test split, cross-validation, and input range validation |
| No real time-series data for forecasting | Medium | Use seeded sample history and state the limitation clearly |
| Bugs found late | Medium | Write tests early and test after each phase |
| Demo fails on the day | High | Keep a recorded backup demo video and a local copy of everything |

## 14. Milestones and Timeline (about 3 weeks)

| Phase | Days | Deliverable |
|---|---|---|
| 1. Setup and planning | 1 | Repo, folder structure, PRD/SRS |
| 2. ML pipeline | 2-6 | Trained and compared models, saved artifacts |
| 3. Backend core | 7-11 | Auth, database, prediction API, history |
| 4. Forecast and real-time | 12-15 | Weekly forecast, live session endpoint |
| 5. Admin and retraining | 16-17 | Upload, retrain, model versioning |
| 6. Frontend | 18-19 | Simple working pages |
| 7. Testing and documentation | 20-21 | Tests, report, slides, demo video |

## 15. Acceptance Criteria (release readiness)

- A new user can register, log in, and make a prediction.
- Invalid inputs are rejected with clear messages.
- A user can only see their own data; only admins can access admin routes.
- A live session runs and stores readings and a final summary.
- The weekly forecast returns a value for users with and without history.
- Admin retraining creates a new model version and activates it only when it is better.
- Swagger documentation lists all endpoints.
- README, report, and demo video are complete.

## 16. Future Scope

- Integration with real wearable devices and health APIs.
- Deep sequence models (LSTM) trained on real time-series data for better forecasting.
- User activity clustering and personalized recommendations.
- CNN-based exercise or food recognition from photos.
- Mobile app and cloud deployment.

## 17. Open Questions

- Which database will be used for the final demo (SQLite or MySQL/PostgreSQL)?
- Will the project be deployed online or demonstrated locally?
- Is a printed report required in a specific university format?
