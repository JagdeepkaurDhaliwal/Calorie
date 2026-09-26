from datetime import UTC, datetime, date
import logging
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Exercise, User, Workout, WorkoutExercise
from app.schemas import (
    BodyCalorieMapResponse,
    BodyPartCalorieDetail,
    WorkoutExerciseCreate,
    WorkoutExerciseOut,
)

logger = logging.getLogger(__name__)

STANDARD_BODY_PARTS = [
    {"id": "chest", "name": "Chest", "icon": "chest", "description": "Pectorals, upper & lower chest"},
    {"id": "back", "name": "Back", "icon": "back", "description": "Lats, rhomboids, traps, lower back"},
    {"id": "legs", "name": "Legs", "icon": "legs", "description": "Quadriceps, hamstrings, glutes, calves"},
    {"id": "biceps", "name": "Biceps", "icon": "biceps", "description": "Front upper arms, brachialis"},
    {"id": "triceps", "name": "Triceps", "icon": "triceps", "description": "Back upper arms, long & lateral heads"},
    {"id": "shoulders", "name": "Shoulders", "icon": "shoulders", "description": "Anterior, lateral, posterior deltoids"},
    {"id": "full_body", "name": "Full Body", "icon": "full_body", "description": "Compound, athletic, whole body"},
]

DEFAULT_EXERCISES = [
    # Strength - Chest
    {"name": "Bench Press", "category": "strength", "body_part": "chest", "default_met": 6.0, "description": "Flat barbell bench press for overall chest power"},
    {"name": "Incline Bench Press", "category": "strength", "body_part": "chest", "default_met": 5.8, "description": "Upper chest development"},
    {"name": "Chest Fly", "category": "strength", "body_part": "chest", "default_met": 4.5, "description": "Dumbbell or cable isolation for chest width"},
    {"name": "Push-up", "category": "strength", "body_part": "chest", "default_met": 4.0, "description": "Bodyweight chest & triceps endurance"},
    {"name": "Dips (Chest Focus)", "category": "strength", "body_part": "chest", "default_met": 5.5, "description": "Lower pectoral & tricep builder"},
    # Strength - Back
    {"name": "Lat Pulldown", "category": "strength", "body_part": "back", "default_met": 5.5, "description": "Wide-grip cable pulldown for lat width"},
    {"name": "Seated Cable Row", "category": "strength", "body_part": "back", "default_met": 5.5, "description": "Mid-back thickness and posture"},
    {"name": "Pull-up", "category": "strength", "body_part": "back", "default_met": 6.5, "description": "Compound vertical pull for back & biceps"},
    {"name": "Barbell Deadlift", "category": "strength", "body_part": "back", "default_met": 7.5, "description": "Full posterior chain powerhouse"},
    {"name": "Bent-over Barbell Row", "category": "strength", "body_part": "back", "default_met": 6.0, "description": "Upper and middle back builder"},
    # Strength - Legs
    {"name": "Barbell Squat", "category": "strength", "body_part": "legs", "default_met": 7.0, "description": "Primary lower-body compound builder"},
    {"name": "Leg Press", "category": "strength", "body_part": "legs", "default_met": 5.5, "description": "Quadriceps & glutes machine drive"},
    {"name": "Walking Lunges", "category": "strength", "body_part": "legs", "default_met": 6.0, "description": "Unilateral leg strength and stability"},
    {"name": "Leg Extension", "category": "strength", "body_part": "legs", "default_met": 4.5, "description": "Isolated quadricep extension"},
    {"name": "Hamstring Leg Curl", "category": "strength", "body_part": "legs", "default_met": 4.5, "description": "Hamstring knee flexion isolation"},
    {"name": "Calf Raise", "category": "strength", "body_part": "legs", "default_met": 4.0, "description": "Gastrocnemius & soleus ankle extension"},
    # Strength - Biceps
    {"name": "Barbell Bicep Curl", "category": "strength", "body_part": "biceps", "default_met": 4.8, "description": "Classic bicep mass builder"},
    {"name": "Hammer Curl", "category": "strength", "body_part": "biceps", "default_met": 4.5, "description": "Brachialis and forearm thickness"},
    {"name": "Preacher Curl", "category": "strength", "body_part": "biceps", "default_met": 4.5, "description": "Strict isolated bicep peak builder"},
    {"name": "Incline Dumbbell Curl", "category": "strength", "body_part": "biceps", "default_met": 4.5, "description": "Long-head bicep stretch focus"},
    # Strength - Triceps
    {"name": "Tricep Rope Pushdown", "category": "strength", "body_part": "triceps", "default_met": 4.8, "description": "Cable tricep extension for lateral head"},
    {"name": "Skull Crusher", "category": "strength", "body_part": "triceps", "default_met": 5.0, "description": "Lying triceps extension for mass"},
    {"name": "Overhead Tricep Extension", "category": "strength", "body_part": "triceps", "default_met": 4.8, "description": "Long-head tricep stretch & burn"},
    {"name": "Close-Grip Bench Press", "category": "strength", "body_part": "triceps", "default_met": 5.8, "description": "Compound tricep press"},
    # Strength - Shoulders
    {"name": "Overhead Shoulder Press", "category": "strength", "body_part": "shoulders", "default_met": 6.0, "description": "Primary anterior & medial deltoid press"},
    {"name": "Dumbbell Lateral Raise", "category": "strength", "body_part": "shoulders", "default_met": 4.5, "description": "Medial deltoid side shoulder width"},
    {"name": "Front Plate Raise", "category": "strength", "body_part": "shoulders", "default_met": 4.2, "description": "Anterior deltoid elevation"},
    {"name": "Face Pull", "category": "strength", "body_part": "shoulders", "default_met": 4.5, "description": "Posterior deltoid and rotator cuff health"},
    # Strength - Full Body
    {"name": "Clean and Press", "category": "strength", "body_part": "full_body", "default_met": 8.0, "description": "Olympic full-body power compound"},
    {"name": "Kettlebell Swing", "category": "strength", "body_part": "full_body", "default_met": 7.5, "description": "Hip hinge explosive power"},
    {"name": "Burpees", "category": "strength", "body_part": "full_body", "default_met": 8.0, "description": "Full-body bodyweight conditioning"},
    # Cardio System
    {"name": "Treadmill Running", "category": "cardio", "body_part": "legs", "default_met": 9.5, "description": "Indoor treadmill run"},
    {"name": "Treadmill Walking", "category": "cardio", "body_part": "legs", "default_met": 4.0, "description": "Incline brisk walk on treadmill"},
    {"name": "Stationary Cycling", "category": "cardio", "body_part": "legs", "default_met": 7.5, "description": "Indoor spin or stationary bike"},
    {"name": "Outdoor Running", "category": "cardio", "body_part": "legs", "default_met": 10.0, "description": "Pavement or trail running"},
    {"name": "Rowing Machine", "category": "cardio", "body_part": "back", "default_met": 7.8, "description": "Full-body low-impact rowing ergometer"},
    {"name": "Elliptical Trainer", "category": "cardio", "body_part": "full_body", "default_met": 6.8, "description": "Smooth elliptical cross-trainer"},
    {"name": "Stair Climber", "category": "cardio", "body_part": "legs", "default_met": 9.0, "description": "Revolving stair climbing workout"},
    {"name": "Jump Rope", "category": "cardio", "body_part": "full_body", "default_met": 10.5, "description": "High-intensity skipping cardio"},
    # Rest / Recovery
    {"name": "Full Body Rest Day", "category": "recovery", "body_part": "full_body", "default_met": 0.0, "description": "Complete physiological rest & muscle repair"},
    {"name": "Foam Rolling & Mobility", "category": "recovery", "body_part": "full_body", "default_met": 0.0, "description": "Myofascial release and joint mobility work"},
    {"name": "Light Stretching & Yoga", "category": "recovery", "body_part": "full_body", "default_met": 0.0, "description": "Active recovery, gentle flexibility and breathing"},
]


def init_default_exercises(db: Session) -> int:
    """Seeds default exercises if database is empty."""
    count = db.query(Exercise).count()
    if count > 0:
        return count
    for item in DEFAULT_EXERCISES:
        ex = Exercise(
            name=item["name"],
            category=item["category"],
            body_part=item["body_part"],
            default_met=item["default_met"],
            description=item.get("description"),
            is_custom=False,
        )
        db.add(ex)
    db.commit()
    logger.info("Seeded %d default exercises.", len(DEFAULT_EXERCISES))
    return len(DEFAULT_EXERCISES)


def get_all_exercises(db: Session, category: str | None = None, body_part: str | None = None) -> list[Exercise]:
    init_default_exercises(db)
    query = db.query(Exercise)
    if category:
        query = query.filter(Exercise.category == category.lower())
    if body_part:
        query = query.filter(Exercise.body_part == body_part.lower())
    return query.order_by(Exercise.category, Exercise.body_part, Exercise.name).all()


def calculate_exercise_calories(user: User, payload: WorkoutExerciseCreate, db: Session | None = None) -> float:
    """
    Computes precise calories for strength, cardio, and recovery.
    Uses the active ML regression model whenever heart rate / cardio parameters are available,
    and calibrated biomechanical work volume equations for strength training.
    """
    if payload.exercise_type == "recovery":
        return 0.0

    # 1. Resolve duration in minutes
    if payload.duration_min is not None and payload.duration_min > 0:
        duration_min = float(payload.duration_min)
    elif payload.duration_hours is not None or payload.duration_minutes is not None:
        duration_min = (float(payload.duration_hours or 0) * 60.0) + float(payload.duration_minutes or 0)
    else:
        duration_min = 20.0  # sensible default

    duration_min = max(duration_min, 1.0)
    weight_kg = float(user.weight_kg) if user.weight_kg else 70.0

    # 2. Strength Exercise Calculation
    if payload.exercise_type == "strength":
        # Base MET expenditure
        met_map = {"low": 3.8, "moderate": 5.0, "high": 6.8}
        met = met_map.get(payload.intensity.lower(), 5.0)

        # Look up exercise-specific MET if available
        if db and payload.exercise_id:
            ex = db.get(Exercise, payload.exercise_id)
            if ex and ex.default_met > 0:
                met = ex.default_met

        # Base aerobic/anaerobic burn
        base_kcal = met * weight_kg * (duration_min / 60.0)

        # Volume mechanical work bonus: Sets x Reps x Weight
        volume_kcal = 0.0
        if payload.sets and payload.reps and payload.weight_kg:
            total_reps = payload.sets * payload.reps
            work_volume = total_reps * payload.weight_kg
            volume_kcal = work_volume * 0.0035

        total = round(base_kcal + volume_kcal, 1)
        return max(total, 12.0)

    # 3. Cardio Exercise Calculation (ML-integrated)
    try:
        from ml.registry import registry
        from ml.features import build_features

        if registry.has_active():
            model = registry.active()
            hr = payload.heart_rate or (115.0 if payload.intensity == "low" else (135.0 if payload.intensity == "moderate" else 155.0))
            age = user.age or 28
            height = user.height_cm or 175.0
            gender = user.gender or "male"
            body_temp = model.estimate_body_temp(min(duration_min, 30.0), hr)

            x = build_features(
                gender=gender,
                age=age,
                height=height,
                weight=weight_kg,
                duration=min(duration_min, 30.0),
                heart_rate=hr,
                body_temp=body_temp,
                meta=model.meta,
            )
            rate_pred = float(model.regressor_predict(x)[0])
            burn_rate = rate_pred / min(duration_min, 30.0)
            total = round(burn_rate * duration_min, 1)
            return max(total, 15.0)
    except Exception as exc:
        logger.warning("ML prediction fallback for cardio: %s", exc)

    # Cardio MET fallback if ML is unavailable
    cardio_met = {"low": 6.0, "moderate": 8.5, "high": 11.0}.get(payload.intensity.lower(), 8.5)
    return round(cardio_met * weight_kg * (duration_min / 60.0), 1)


def log_workout_exercise(db: Session, user: User, payload: WorkoutExerciseCreate) -> tuple[WorkoutExercise, Workout | None]:
    """Persists a detailed workout exercise and syncs with the overall Workout entity."""
    init_default_exercises(db)

    # Resolve duration
    if payload.duration_min is not None and payload.duration_min > 0:
        duration_min = float(payload.duration_min)
    elif payload.duration_hours is not None or payload.duration_minutes is not None:
        duration_min = (float(payload.duration_hours or 0) * 60.0) + float(payload.duration_minutes or 0)
    else:
        duration_min = 20.0

    calories = calculate_exercise_calories(user, payload, db=db)

    # Resolve exercise reference if ID provided
    ex_name = payload.exercise_name
    body_part = payload.body_part.lower()
    if payload.exercise_id:
        ex = db.get(Exercise, payload.exercise_id)
        if ex:
            ex_name = ex.name
            body_part = ex.body_part

    # Create WorkoutExercise record
    we = WorkoutExercise(
        user_id=user.id,
        exercise_id=payload.exercise_id,
        exercise_name=ex_name,
        exercise_type=payload.exercise_type.lower(),
        body_part=body_part,
        sets=payload.sets,
        reps=payload.reps,
        weight_kg=payload.weight_kg,
        duration_min=round(duration_min, 1),
        rest_time_sec=payload.rest_time_sec,
        calories_burned=calories,
        heart_rate=payload.heart_rate,
        distance_km=payload.distance_km,
        intensity=payload.intensity.lower(),
        notes=payload.notes,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(we)

    # Sync to general Workout table for history and forecast consistency
    workout = None
    if calories > 0:
        workout = Workout(
            user_id=user.id,
            duration_min=round(duration_min, 1),
            heart_rate=payload.heart_rate or 125.0,
            body_temp=38.5,
            predicted_calories=calories,
            intensity=payload.intensity.lower(),
            source=payload.exercise_type.lower(),
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(workout)

    db.commit()
    db.refresh(we)
    return we, workout


def get_body_calorie_map(db: Session, user: User, target_date: str | None = None) -> BodyCalorieMapResponse:
    """
    Returns today's (or given date's) calories burned grouped per body part,
    as well as itemized exercise details.
    """
    if not target_date:
        target_date = datetime.now(UTC).strftime("%Y-%m-%d")

    records = (
        db.query(WorkoutExercise)
        .filter(
            WorkoutExercise.user_id == user.id,
            func.date(WorkoutExercise.created_at) == target_date,
        )
        .order_by(WorkoutExercise.created_at.desc())
        .all()
    )

    body_part_totals: dict[str, float] = {bp["id"]: 0.0 for bp in STANDARD_BODY_PARTS}
    body_part_exercises: dict[str, list[WorkoutExercise]] = {bp["id"]: [] for bp in STANDARD_BODY_PARTS}
    total_exercise_kcal = 0.0

    for rec in records:
        bp = rec.body_part.lower() if rec.body_part else "full_body"
        if bp not in body_part_totals:
            body_part_totals[bp] = 0.0
            body_part_exercises[bp] = []
        body_part_totals[bp] = round(body_part_totals[bp] + rec.calories_burned, 1)
        body_part_exercises[bp].append(rec)
        total_exercise_kcal = round(total_exercise_kcal + rec.calories_burned, 1)

    details = []
    for bp in STANDARD_BODY_PARTS:
        bp_id = bp["id"]
        ex_list = [WorkoutExerciseOut.model_validate(e) for e in body_part_exercises.get(bp_id, [])]
        details.append(
            BodyPartCalorieDetail(
                body_part=bp_id,
                calories=body_part_totals.get(bp_id, 0.0),
                exercise_count=len(ex_list),
                exercises=ex_list,
            )
        )

    return BodyCalorieMapResponse(
        date=target_date,
        total_exercise_calories=total_exercise_kcal,
        body_parts=body_part_totals,
        details=details,
    )
