from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import NotFound
from app.models import Workout


def iso_week_start(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    dt = dt.astimezone(UTC)
    monday = dt.date() - timedelta(days=dt.weekday())
    return datetime(monday.year, monday.month, monday.day, tzinfo=UTC)


def save_workout(
    db: Session,
    *,
    user_id: int,
    duration_min: float,
    heart_rate: float,
    body_temp: float,
    predicted_calories: float,
    intensity: str,
    model_version_id: int | None,
    source: str,
    extrapolated: bool,
    created_at: datetime | None = None,
) -> Workout:
    workout = Workout(
        user_id=user_id,
        duration_min=duration_min,
        heart_rate=heart_rate,
        body_temp=body_temp,
        predicted_calories=predicted_calories,
        intensity=intensity,
        model_version_id=model_version_id,
        source=source,
        extrapolated=extrapolated,
        created_at=created_at or datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(workout)
    db.commit()
    db.refresh(workout)
    return workout


def list_workouts(db: Session, user_id: int, page: int, page_size: int) -> tuple[list[Workout], int]:
    query = db.query(Workout).filter(Workout.user_id == user_id)
    total = query.count()
    items = (
        query.order_by(Workout.created_at.desc(), Workout.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def delete_workout(db: Session, user_id: int, workout_id: int) -> None:
    workout = db.query(Workout).filter(Workout.id == workout_id, Workout.user_id == user_id).first()
    if not workout:
        raise NotFound("Workout not found")
    db.delete(workout)
    db.commit()


def summary(db: Session, user_id: int) -> dict:
    now = datetime.now(UTC)
    week_start = iso_week_start(now).replace(tzinfo=None)
    week_q = db.query(func.coalesce(func.sum(Workout.predicted_calories), 0.0)).filter(
        Workout.user_id == user_id, Workout.created_at >= week_start
    )
    week_total = float(week_q.scalar() or 0)
    agg = db.query(
        func.coalesce(func.avg(Workout.predicted_calories), 0.0),
        func.count(Workout.id),
    ).filter(Workout.user_id == user_id).one()
    avg, count = float(agg[0] or 0), int(agg[1] or 0)
    return {
        "week_total": round(week_total, 1),
        "avg_per_workout": round(avg, 1),
        "count": count,
    }
