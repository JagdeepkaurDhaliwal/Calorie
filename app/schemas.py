from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from ml.config import RANGES


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("email")
    @classmethod
    def email_has_at(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("invalid email format")
        return v.lower().strip()


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserPublic(BaseModel):
    id: int
    name: str
    email: str
    role: str
    age: int | None = None
    gender: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    fitness_goal: str | None = None
    preferred_workout_type: str | None = None
    preferred_body_parts: str | None = None
    daily_calorie_target: float | None = 2000.0
    dietary_preference: str | None = None

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    age: int | None = Field(default=None, ge=RANGES["age"][0], le=RANGES["age"][1])
    gender: str | None = None
    height_cm: float | None = Field(default=None, ge=RANGES["height"][0], le=RANGES["height"][1])
    weight_kg: float | None = Field(default=None, ge=RANGES["weight"][0], le=RANGES["weight"][1])
    fitness_goal: str | None = None
    preferred_workout_type: str | None = None
    preferred_body_parts: str | None = None
    daily_calorie_target: float | None = Field(default=None, ge=800.0, le=8000.0)
    dietary_preference: str | None = None

    @field_validator("gender")
    @classmethod
    def gender_ok(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.lower()
        if v not in ("male", "female"):
            raise ValueError("gender must be male or female")
        return v


class PredictRequest(BaseModel):
    duration: float | None = Field(default=None, ge=RANGES["duration"][0], le=RANGES["duration"][1])
    duration_hours: float | None = Field(default=None, ge=0.0, le=24.0)
    duration_minutes: float | None = Field(default=None, ge=0.0, le=59.9)
    heart_rate: float | None = Field(default=None, ge=RANGES["heart_rate"][0], le=RANGES["heart_rate"][1])
    body_temp: float | None = Field(default=None, ge=35.0, le=108.0)
    body_temp_unit: str = Field(default="C")
    gender: str | None = None
    age: int | None = Field(default=None, ge=RANGES["age"][0], le=RANGES["age"][1])
    height: float | None = Field(default=None, ge=10.0, le=250.0)
    height_unit: str = Field(default="cm")
    height_feet: float | None = Field(default=None, ge=3.0, le=8.0)
    height_inches: float | None = Field(default=None, ge=0.0, le=11.9)
    weight: float | None = Field(default=None, ge=20.0, le=500.0)
    weight_unit: str = Field(default="kg")
    intensity: str | None = None
    workout_type: str | None = None

    @field_validator("gender")
    @classmethod
    def gender_ok(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.lower()
        if v not in ("male", "female"):
            raise ValueError("gender must be male or female")
        return v


class PredictResponse(BaseModel):
    workout_id: int
    predicted_calories: float
    intensity: str
    model_version: int
    extrapolated: bool
    warnings: list[str]


class WorkoutOut(BaseModel):
    id: int
    duration_min: float
    heart_rate: float
    body_temp: float
    predicted_calories: float
    intensity: str
    model_version_id: int | None
    source: str
    extrapolated: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedWorkouts(BaseModel):
    items: list[WorkoutOut]
    total: int
    page: int
    page_size: int


class WorkoutSummary(BaseModel):
    week_total: float
    avg_per_workout: float
    count: int


class ForecastResponse(BaseModel):
    method: str
    weekly_total: float
    daily: list[float]


class SessionStartRequest(BaseModel):
    body_temp: float | None = Field(default=None, ge=RANGES["body_temp"][0], le=RANGES["body_temp"][1])


class SessionStartResponse(BaseModel):
    session_id: int
    started_at: datetime


class ReadingIn(BaseModel):
    heart_rate: int = Field(ge=int(RANGES["heart_rate"][0]), le=int(RANGES["heart_rate"][1]))
    interval_sec: int = Field(default=5, ge=1, le=60)


class SessionUpdate(BaseModel):
    elapsed_sec: int
    avg_hr: float
    cumulative_calories: float
    intensity_so_far: str


class SessionSummary(BaseModel):
    total_calories: float
    duration_min: float
    avg_hr: float
    intensity: str
    workout_id: int | None = None


class RetrainRequest(BaseModel):
    dataset_id: int | None = None


class HealthResponse(BaseModel):
    status: str
    active_model_version: int | None = None


# --- Exercise & Workout Systems ---
class ExerciseOut(BaseModel):
    id: int
    name: str
    category: str
    body_part: str
    description: str | None = None
    default_met: float = 5.0
    is_custom: bool = False

    model_config = {"from_attributes": True}


class WorkoutExerciseCreate(BaseModel):
    exercise_id: int | None = None
    exercise_name: str
    exercise_type: str = "strength"  # "strength", "cardio", "recovery"
    body_part: str = "full_body"  # "chest", "back", "legs", "biceps", "triceps", "shoulders", "full_body"
    sets: int | None = None
    reps: int | None = None
    weight_kg: float | None = None
    duration_min: float | None = None
    duration_hours: float | None = None
    duration_minutes: float | None = None
    rest_time_sec: int | None = None
    heart_rate: float | None = None
    distance_km: float | None = None
    intensity: str = "moderate"
    notes: str | None = None


class WorkoutExerciseOut(BaseModel):
    id: int
    exercise_name: str
    exercise_type: str
    body_part: str
    sets: int | None = None
    reps: int | None = None
    weight_kg: float | None = None
    duration_min: float
    rest_time_sec: int | None = None
    calories_burned: float
    heart_rate: float | None = None
    distance_km: float | None = None
    intensity: str
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BodyPartCalorieDetail(BaseModel):
    body_part: str
    calories: float
    exercise_count: int
    exercises: list[WorkoutExerciseOut] = []


class BodyCalorieMapResponse(BaseModel):
    date: str
    total_exercise_calories: float
    body_parts: dict[str, float]
    details: list[BodyPartCalorieDetail]


# --- Nutrition & Meal Tracking ---
class MealItemCreate(BaseModel):
    food_name: str
    quantity: str
    calories: float
    protein: float = 0.0
    carbs: float = 0.0
    fat: float = 0.0


class MealItemOut(BaseModel):
    id: int
    food_name: str
    quantity: str
    calories: float
    protein: float
    carbs: float
    fat: float
    is_ai_detected: bool

    model_config = {"from_attributes": True}


class MealCreate(BaseModel):
    meal_type: str  # "breakfast", "lunch", "dinner", "snack"
    date: str | None = None
    items: list[MealItemCreate] = []


class MealOut(BaseModel):
    id: int
    meal_type: str
    date: str
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    items: list[MealItemOut]
    created_at: datetime

    model_config = {"from_attributes": True}


class DailyNutritionSummary(BaseModel):
    date: str
    daily_target: float
    consumed_calories: float
    remaining_calories: float
    exercise_calories: float
    net_calories: float
    status: str
    status_message: str
    total_protein: float
    total_carbs: float
    total_fat: float
    meals: dict[str, MealOut | None]


class FoodItemOut(BaseModel):
    id: int
    name: str
    category: str
    serving_size: str
    calories: float
    protein: float
    carbs: float
    fat: float

    model_config = {"from_attributes": True}


class FoodAnalysisItem(BaseModel):
    name: str
    portion: str
    calories: float
    protein: float
    carbs: float
    fat: float


class FoodAnalysisResponse(BaseModel):
    analysis_id: int
    image_url: str
    detected_items: list[FoodAnalysisItem]
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    suggested_meal: str


class FoodConfirmRequest(BaseModel):
    analysis_id: int | None = None
    meal_type: str
    date: str | None = None
    items: list[MealItemCreate]


class FoodRecommendationOut(BaseModel):
    food_name: str
    portion: str
    calories: float
    protein: float
    carbs: float
    fat: float
    suggested_meal: str
    reason: str


# --- AI Fitness Agent ---
class PersonalizedPlanRequest(BaseModel):
    goal: str = "muscle_building"
    preferred_body_parts: list[str] = []
    dietary_preference: str = "balanced"
    target_calories: float | None = None
    workout_days_per_week: int = 4


class AIPlanResponse(BaseModel):
    id: int
    plan_type: str
    goal: str
    title: str
    summary: str
    workout_plan: dict
    nutrition_plan: dict
    daily_calorie_target: float
    created_at: datetime


class AIChatRequest(BaseModel):
    message: str


class AIChatResponse(BaseModel):
    reply: str
    suggested_actions: list[str] = []
