def test_get_body_parts(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    res = client.get("/exercises/body-parts", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 7
    ids = [bp["id"] for bp in data]
    assert "chest" in ids
    assert "back" in ids
    assert "legs" in ids
    assert "biceps" in ids
    assert "triceps" in ids
    assert "shoulders" in ids
    assert "full_body" in ids


def test_list_exercises(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    res = client.get("/exercises", headers=headers)
    assert res.status_code == 200
    exercises = res.json()
    assert len(exercises) >= 20

    # Filter by body part
    res_chest = client.get("/exercises?body_part=chest", headers=headers)
    assert res_chest.status_code == 200
    chest_exercises = res_chest.json()
    assert all(e["body_part"] == "chest" for e in chest_exercises)
    assert any("Bench Press" in e["name"] for e in chest_exercises)


def test_record_strength_workout_exercise(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    payload = {
        "exercise_name": "Bench Press",
        "exercise_type": "strength",
        "body_part": "chest",
        "sets": 4,
        "reps": 10,
        "weight_kg": 60.0,
        "duration_min": 25.0,
        "rest_time_sec": 90,
        "intensity": "moderate",
    }
    res = client.post("/exercises/workout", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["exercise_name"] == "Bench Press"
    assert data["body_part"] == "chest"
    assert data["calories_burned"] > 0
    assert data["sets"] == 4
    assert data["reps"] == 10


def test_record_cardio_workout_exercise(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    payload = {
        "exercise_name": "Treadmill Running",
        "exercise_type": "cardio",
        "body_part": "legs",
        "duration_min": 30.0,
        "heart_rate": 145.0,
        "distance_km": 4.5,
        "intensity": "high",
    }
    res = client.post("/exercises/workout", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["calories_burned"] > 50.0
    assert data["body_part"] == "legs"


def test_body_calorie_map(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    # Log chest workout
    client.post(
        "/exercises/workout",
        json={
            "exercise_name": "Chest Fly",
            "exercise_type": "strength",
            "body_part": "chest",
            "sets": 3,
            "reps": 12,
            "weight_kg": 20.0,
            "duration_min": 15.0,
        },
        headers=headers,
    )
    # Log legs workout
    client.post(
        "/exercises/workout",
        json={
            "exercise_name": "Barbell Squat",
            "exercise_type": "strength",
            "body_part": "legs",
            "sets": 4,
            "reps": 8,
            "weight_kg": 70.0,
            "duration_min": 20.0,
        },
        headers=headers,
    )

    res = client.get("/workouts/body-part-summary", headers=headers)
    assert res.status_code == 200
    map_data = res.json()
    assert "body_parts" in map_data
    assert map_data["body_parts"]["chest"] > 0
    assert map_data["body_parts"]["legs"] > 0
    assert map_data["total_exercise_calories"] > 0
    assert len(map_data["details"]) >= 7
