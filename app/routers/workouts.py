from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import PaginatedWorkouts, WorkoutOut, WorkoutSummary
from app.security import get_current_user
from app.services.workout_service import delete_workout, list_workouts, summary

router = APIRouter(prefix="/workouts", tags=["workouts"])


@router.get("", response_model=PaginatedWorkouts)
def get_workouts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = list_workouts(db, current_user.id, page, page_size)
    return PaginatedWorkouts(
        items=[WorkoutOut.model_validate(w) for w in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=WorkoutSummary)
def get_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = summary(db, current_user.id)
    return WorkoutSummary(**data)


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    delete_workout(db, current_user.id, workout_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
