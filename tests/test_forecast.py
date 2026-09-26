from datetime import UTC, datetime, timedelta

from app.models import Workout
from app.services.workout_service import save_workout


def test_tc8_forecast_with_no_history(client, user_token):
    resp = client.get("/forecast/weekly", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["method"] == "fallback"
    assert data["weekly_total"] > 0
    assert len(data["daily"]) == 7
    assert sum(data["daily"]) == pytest.approx(data["weekly_total"], abs=0.5)


def test_forecast_with_three_complete_weeks(client, db_session, normal_user, user_token):
    now = datetime.now(UTC)
    # Seed 3 workouts spread across 3 distinct past complete weeks
    for w in [1, 2, 3]:
        past_dt = now - timedelta(weeks=w, days=2)
        save_workout(
            db_session,
            user_id=normal_user.id,
            duration_min=30.0,
            heart_rate=120.0,
            body_temp=38.0,
            predicted_calories=150.0,
            intensity="moderate",
            model_version_id=1,
            source="seed",
            extrapolated=False,
            created_at=past_dt.replace(tzinfo=None),
        )

    resp = client.get("/forecast/weekly", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["method"] == "history"
    assert data["weekly_total"] > 0
    assert len(data["daily"]) == 7


import pytest
