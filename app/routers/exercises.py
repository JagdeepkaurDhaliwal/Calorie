from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, WorkoutExercise
from app.schemas import (
    BodyCalorieMapResponse,
    ExerciseOut,
    WorkoutExerciseCreate,
    WorkoutExerciseOut,
)
from app.security import get_current_user
from app.services.exercise_service import (
    STANDARD_BODY_PARTS,
    get_all_exercises,
    get_body_calorie_map,
    log_workout_exercise,
)

router = APIRouter(tags=["exercises"])


@router.get("/exercises", response_model=list[ExerciseOut])
def list_exercises(
    category: str | None = Query(default=None),
    body_part: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_all_exercises(db, category=category, body_part=body_part)


@router.get("/exercises/body-parts")
def list_body_parts(current_user: User = Depends(get_current_user)):
    return STANDARD_BODY_PARTS


@router.post("/exercises/workout", response_model=WorkoutExerciseOut, status_code=status.HTTP_201_CREATED)
def record_workout_exercise(
    payload: WorkoutExerciseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    we, _ = log_workout_exercise(db, current_user, payload)
    return WorkoutExerciseOut.model_validate(we)


@router.get("/workouts/body-part-summary", response_model=BodyCalorieMapResponse)
def get_user_body_calorie_map(
    date: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_body_calorie_map(db, current_user, target_date=date)


@router.get("/exercises/history", response_model=list[WorkoutExerciseOut])
def get_exercise_history(
    body_part: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(WorkoutExercise).filter(WorkoutExercise.user_id == current_user.id)
    if body_part:
        query = query.filter(WorkoutExercise.body_part == body_part.lower())
    records = query.order_by(WorkoutExercise.created_at.desc()).limit(limit).all()
    return [WorkoutExerciseOut.model_validate(r) for r in records]
