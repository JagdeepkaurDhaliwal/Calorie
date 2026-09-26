from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import User, Workout
from app.services.prediction_service import predict_from_inputs
from ml.registry import registry


def _weekly_totals(db: Session, user_id: int, last_n: int = 8) -> list[float]:
    rows = (
        db.query(Workout)
        .filter(Workout.user_id == user_id)
        .order_by(Workout.created_at.asc())
        .all()
    )
    if not rows:
        return []
    buckets: dict[tuple[int, int], float] = {}
    for row in rows:
        dt = row.created_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        iso = dt.isocalendar()
        key = (iso.year, iso.week)
        buckets[key] = buckets.get(key, 0.0) + float(row.predicted_calories)
    keys = sorted(buckets.keys())
    now = datetime.now(UTC)
    current = now.isocalendar()
    current_key = (current.year, current.week)
    complete = [k for k in keys if k != current_key][-last_n:]
    return [buckets[k] for k in complete]


def ema(values: list[float], alpha: float = 0.5) -> float:
    s = float(values[0])
    for x in values[1:]:
        s = alpha * float(x) + (1 - alpha) * s
    return s


def _weekday_shares(db: Session, user_id: int) -> list[float] | None:
    rows = db.query(Workout).filter(Workout.user_id == user_id).all()
    if not rows:
        return None
    counts = [0.0] * 7
    for row in rows:
        dt = row.created_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        counts[dt.weekday()] += float(row.predicted_calories)
    total = sum(counts)
    if total <= 0:
        return None
    return [c / total for c in counts]


def _fallback_weekly(db: Session, user: User) -> float:
    recent = (
        db.query(Workout)
        .filter(Workout.user_id == user.id)
        .order_by(Workout.created_at.desc())
        .limit(10)
        .all()
    )
    if recent:
        mean_cal = sum(w.predicted_calories for w in recent) / len(recent)
        all_rows = db.query(Workout).filter(Workout.user_id == user.id).all()
        weeks = set()
        for row in all_rows:
            dt = row.created_at.replace(tzinfo=UTC) if row.created_at.tzinfo is None else row.created_at
            iso = dt.isocalendar()
            weeks.add((iso.year, iso.week))
        per_week = max(len(all_rows) / max(len(weeks), 1), 1.0)
        return mean_cal * per_week

    age = user.age or 30
    hr = 0.65 * (220 - age)
    gender = user.gender or "male"
    height = user.height_cm or 170.0
    weight = user.weight_kg or 70.0
    if not registry.has_active():
        return 3 * 150.0
    result = predict_from_inputs(
        {
            "gender": gender,
            "age": age,
            "height": height,
            "weight": weight,
            "duration": 30.0,
            "heart_rate": hr,
            "body_temp": 39.0,
        }
    )
    return 3 * result.kcal


def weekly_forecast(db: Session, user: User) -> dict:
    totals = _weekly_totals(db, user.id, last_n=8)
    if len(totals) >= 3:
        weekly = ema(totals, alpha=0.5)
        method = "history"
    else:
        weekly = _fallback_weekly(db, user)
        method = "fallback"
    shares = _weekday_shares(db, user.id) or [1 / 7] * 7
    return {
        "method": method,
        "weekly_total": round(float(weekly), 1),
        "daily": [round(float(weekly) * s, 1) for s in shares],
    }
