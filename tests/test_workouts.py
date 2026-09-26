from app.models import Workout
from app.services.workout_service import save_workout


def test_tc7_user_data_isolation(client, db_session, normal_user, other_user, user_token, other_token):
    # Save a workout for other_user
    w_other = save_workout(
        db_session,
        user_id=other_user.id,
        duration_min=30.0,
        heart_rate=120.0,
        body_temp=38.0,
        predicted_calories=150.0,
        intensity="moderate",
        model_version_id=1,
        source="manual",
        extrapolated=False,
    )

    # Save a workout for normal_user
    w_user = save_workout(
        db_session,
        user_id=normal_user.id,
        duration_min=20.0,
        heart_rate=110.0,
        body_temp=38.0,
        predicted_calories=95.0,
        intensity="low",
        model_version_id=1,
        source="manual",
        extrapolated=False,
    )

    # Normal user lists workouts
    resp = client.get("/workouts", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    ids = [item["id"] for item in items]
    assert w_user.id in ids
    assert w_other.id not in ids  # Other user's workout is never visible

    # Normal user tries to delete other user's workout
    del_resp = client.delete(f"/workouts/{w_other.id}", headers={"Authorization": f"Bearer {user_token}"})
    assert del_resp.status_code == 404  # 404 Not Found to prevent ID enumeration


def test_workout_summary(client, db_session, normal_user, user_token):
    save_workout(
        db_session,
        user_id=normal_user.id,
        duration_min=20.0,
        heart_rate=110.0,
        body_temp=38.0,
        predicted_calories=100.0,
        intensity="low",
        model_version_id=1,
        source="manual",
        extrapolated=False,
    )
    save_workout(
        db_session,
        user_id=normal_user.id,
        duration_min=30.0,
        heart_rate=130.0,
        body_temp=38.5,
        predicted_calories=200.0,
        intensity="moderate",
        model_version_id=1,
        source="manual",
        extrapolated=False,
    )

    resp = client.get("/workouts/summary", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert data["avg_per_workout"] == 150.0
    assert data["week_total"] == 300.0
