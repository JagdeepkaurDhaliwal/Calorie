import json
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
        CheckConstraint("gender IS NULL OR gender IN ('male', 'female')", name="ck_users_gender"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False, default="user")
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    fitness_goal: Mapped[str | None] = mapped_column(String(50), nullable=True)
    preferred_workout_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    preferred_body_parts: Mapped[str | None] = mapped_column(String(255), nullable=True)
    daily_calorie_target: Mapped[float | None] = mapped_column(Float, nullable=True, default=2000.0)
    dietary_preference: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    workouts: Mapped[list["Workout"]] = relationship(back_populates="user")
    sessions: Mapped[list["Session"]] = relationship(back_populates="user")
    workout_exercises: Mapped[list["WorkoutExercise"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    meals: Mapped[list["Meal"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    ai_plans: Mapped[list["AIPlan"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        Index(
            "uq_one_active_model",
            "is_active",
            unique=True,
            sqlite_where=text("is_active = 1"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)
    artifact_dir: Mapped[str] = mapped_column(String(255), nullable=False)
    mae: Mapped[float] = mapped_column(Float, nullable=False)
    rmse: Mapped[float] = mapped_column(Float, nullable=False)
    r2: Mapped[float] = mapped_column(Float, nullable=False)
    clf_accuracy: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    clf_f1: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    candidates_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    training_job_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("training_jobs.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    workouts: Mapped[list["Workout"]] = relationship(back_populates="model_version")

    def candidates(self) -> dict:
        if not self.candidates_json:
            return {}
        return json.loads(self.candidates_json)


class Workout(Base):
    __tablename__ = "workouts"
    __table_args__ = (Index("ix_workouts_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    duration_min: Mapped[float] = mapped_column(Float, nullable=False)
    heart_rate: Mapped[float] = mapped_column(Float, nullable=False)
    body_temp: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_calories: Mapped[float] = mapped_column(Float, nullable=False)
    intensity: Mapped[str] = mapped_column(String(10), nullable=False)
    model_version_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("model_versions.id"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="manual")
    extrapolated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="workouts")
    model_version: Mapped["ModelVersion | None"] = relationship(back_populates="workouts")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    elapsed_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hr_sum: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reading_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    body_temp_input: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_calories: Mapped[float | None] = mapped_column(Float, nullable=True)
    intensity: Mapped[str | None] = mapped_column(String(10), nullable=True)

    user: Mapped["User"] = relationship(back_populates="sessions")
    readings: Mapped[list["Reading"]] = relationship(back_populates="session")


class Reading(Base):
    __tablename__ = "readings"
    __table_args__ = (Index("ix_readings_session_ts", "session_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("sessions.id"), nullable=False)
    heart_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    interval_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    elapsed_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    cumulative_calories: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)


    session: Mapped["Session"] = relationship(back_populates="readings")


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(255), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(15), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("datasets.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="queued")
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    activated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False)  # "strength", "cardio", "recovery"
    body_part: Mapped[str] = mapped_column(String(30), nullable=False)  # "chest", "back", "legs", "biceps", "triceps", "shoulders", "full_body", "cardio"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_met: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    is_custom: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"
    __table_args__ = (Index("ix_workout_exercises_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    exercise_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("exercises.id"), nullable=True)
    exercise_name: Mapped[str] = mapped_column(String(100), nullable=False)
    exercise_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "strength", "cardio", "recovery"
    body_part: Mapped[str] = mapped_column(String(30), nullable=False)  # "chest", "back", "legs", "biceps", "triceps", "shoulders", "full_body"
    sets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_min: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rest_time_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calories_burned: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    heart_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    intensity: Mapped[str] = mapped_column(String(20), nullable=False, default="moderate")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="workout_exercises")
    exercise: Mapped["Exercise | None"] = relationship()


class Meal(Base):
    __tablename__ = "meals"
    __table_args__ = (Index("ix_meals_user_date", "user_id", "date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    meal_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "breakfast", "lunch", "dinner", "snack"
    date: Mapped[str] = mapped_column(String(10), nullable=False)  # "YYYY-MM-DD"
    total_calories: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_protein: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_carbs: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_fat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="meals")
    items: Mapped[list["MealItem"]] = relationship(back_populates="meal", cascade="all, delete-orphan")


class MealItem(Base):
    __tablename__ = "meal_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meal_id: Mapped[int] = mapped_column(Integer, ForeignKey("meals.id"), nullable=False, index=True)
    food_name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[str] = mapped_column(String(50), nullable=False)
    calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    carbs: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_ai_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    meal: Mapped["Meal"] = relationship(back_populates="items")


class FoodItem(Base):
    __tablename__ = "food_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    serving_size: Mapped[str] = mapped_column(String(50), nullable=False)
    calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein: Mapped[float] = mapped_column(Float, nullable=False)
    carbs: Mapped[float] = mapped_column(Float, nullable=False)
    fat: Mapped[float] = mapped_column(Float, nullable=False)


class FoodAnalysis(Base):
    __tablename__ = "food_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    image_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    detected_items_json: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_calories: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_protein: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_carbs: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_fat: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_review")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class AIPlan(Base):
    __tablename__ = "ai_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "general", "personalized"
    goal: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    workout_plan_json: Mapped[str] = mapped_column(Text, nullable=False)
    nutrition_plan_json: Mapped[str] = mapped_column(Text, nullable=False)
    daily_calorie_target: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="ai_plans")
