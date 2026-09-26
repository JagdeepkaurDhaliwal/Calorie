from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.errors import BadRequest, Conflict, NotFound, ValidationError
from app.models import Reading, Session as WorkoutSession, User
from app.services.prediction_service import predict_from_inputs
from app.services.workout_service import save_workout
from ml.registry import registry


STALE_AFTER = timedelta(hours=3)


def close_stale_sessions(db: Session) -> int:
    cutoff = datetime.now(UTC).replace(tzinfo=None) - STALE_AFTER
    stale = (
        db.query(WorkoutSession)
        .filter(WorkoutSession.status == "active", WorkoutSession.started_at < cutoff)
        .all()
    )
    count = 0
    for session in stale:
        session.status = "ended"
        session.ended_at = datetime.now(UTC).replace(tzinfo=None)
        count += 1
    if count:
        db.commit()
    return count


def start_session(db: Session, user: User, body_temp: float | None) -> WorkoutSession:
    _profile_inputs(user)
    existing = (
        db.query(WorkoutSession)
        .filter(WorkoutSession.user_id == user.id, WorkoutSession.status == "active")
        .first()
    )
    if existing:
        raise Conflict("You already have an active session")
    session = WorkoutSession(
        user_id=user.id,
        status="active",
        started_at=datetime.now(UTC).replace(tzinfo=None),
        body_temp_input=body_temp,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _owned_session(db: Session, user: User, session_id: int) -> WorkoutSession:
    session = db.query(WorkoutSession).filter(WorkoutSession.id == session_id).first()
    if not session or session.user_id != user.id:
        raise NotFound("Session not found")
    return session


def get_owned_active_session(db: Session, user: User, session_id: int) -> WorkoutSession:
    session = _owned_session(db, user, session_id)
    if session.status != "active":
        raise Conflict("Session already ended")
    return session


def _profile_inputs(user: User) -> dict:
    missing = [
        name
        for name, value in (
            ("gender", user.gender),
            ("age", user.age),
            ("height", user.height_cm),
            ("weight", user.weight_kg),
        )
        if value is None
    ]
    if missing:
        raise ValidationError(
            "Complete your profile before starting a live session",
            details=[{"field": f, "issue": "required"} for f in missing],
        )
    return {
        "gender": user.gender,
        "age": user.age,
        "height": user.height_cm,
        "weight": user.weight_kg,
    }


def _previous_cumulative(db: Session, session_id: int) -> float:
    last = (
        db.query(Reading)
        .filter(Reading.session_id == session_id)
        .order_by(Reading.id.desc())
        .first()
    )
    return float(last.cumulative_calories) if last else 0.0


def compute_live_calories(user: User, session: WorkoutSession, elapsed_sec: int, avg_hr: float) -> tuple[float, str, bool]:
    elapsed_min = elapsed_sec / 60.0
    duration_for_model = max(elapsed_min, 1.0)
    if session.body_temp_input is not None:
        body_temp = float(session.body_temp_input)
    else:
        body_temp = registry.active().estimate_body_temp(duration_for_model, avg_hr)
    profile = _profile_inputs(user)
    result = predict_from_inputs(
        {
            **profile,
            "duration": duration_for_model,
            "heart_rate": avg_hr,
            "body_temp": body_temp,
        }
    )
    kcal = result.kcal
    if elapsed_min < 1:
        kcal = kcal * elapsed_min
    return round(max(kcal, 0.0), 2), result.intensity, result.extrapolated


def add_reading(db: Session, user: User, session: WorkoutSession, heart_rate: int, interval_sec: int) -> dict:
    if session.status != "active":
        raise Conflict("Session already ended")
    session.elapsed_sec += int(interval_sec)
    session.hr_sum += float(heart_rate)
    session.reading_count += 1
    avg_hr = session.hr_sum / session.reading_count
    kcal, intensity, _ = compute_live_calories(user, session, session.elapsed_sec, avg_hr)
    prev = _previous_cumulative(db, session.id)
    kcal = max(kcal, prev)
    reading = Reading(
        session_id=session.id,
        heart_rate=int(heart_rate),
        interval_sec=int(interval_sec),
        elapsed_sec=session.elapsed_sec,
        cumulative_calories=kcal,
        timestamp=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(reading)
    db.commit()
    db.refresh(session)
    return {
        "elapsed_sec": session.elapsed_sec,
        "avg_hr": round(avg_hr, 1),
        "cumulative_calories": round(kcal, 2),
        "intensity_so_far": intensity,
    }


def finish_session(db: Session, user: User, session: WorkoutSession) -> dict:
    if session.status != "active":
        raise Conflict("Session already ended")
    if session.reading_count == 0:
        avg_hr = 0.0
        kcal = 0.0
        intensity = "low"
        extrapolated = False
    else:
        avg_hr = session.hr_sum / session.reading_count
        kcal, intensity, extrapolated = compute_live_calories(user, session, session.elapsed_sec, avg_hr)
        prev = _previous_cumulative(db, session.id)
        kcal = max(kcal, prev)
    session.status = "ended"
    session.ended_at = datetime.now(UTC).replace(tzinfo=None)
    session.total_calories = kcal
    session.intensity = intensity
    duration_min = round(session.elapsed_sec / 60.0, 2)
    workout = None
    if session.reading_count > 0:
        body_temp = session.body_temp_input
        if body_temp is None:
            body_temp = registry.active().estimate_body_temp(max(duration_min, 1.0), avg_hr)
        version_id = registry.active().version_id if registry.has_active() else None
        workout = save_workout(
            db,
            user_id=user.id,
            duration_min=max(duration_min, 0.01),
            heart_rate=avg_hr,
            body_temp=float(body_temp),
            predicted_calories=kcal,
            intensity=intensity,
            model_version_id=version_id,
            source="session",
            extrapolated=extrapolated if session.reading_count else False,
        )
    else:
        db.commit()
    db.refresh(session)
    return {
        "total_calories": round(float(kcal), 2),
        "duration_min": duration_min,
        "avg_hr": round(float(avg_hr), 1),
        "intensity": intensity,
        "workout_id": workout.id if workout else None,
    }
