def test_tc5_valid_prediction(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    payload = {
        "duration": 25.0,
        "heart_rate": 115.0,
        "body_temp": 38.5,
        "gender": "female",
        "age": 26,
        "height": 165.0,
        "weight": 60.0,
    }
    response = client.post("/predict", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "workout_id" in data
    assert data["predicted_calories"] > 0
    assert data["intensity"] in ["low", "moderate", "high"]
    assert "model_version" in data
    assert isinstance(data["warnings"], list)


def test_tc6_invalid_heart_rate(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    payload = {
        "duration": 25.0,
        "heart_rate": 400.0,  # Invalid: max is 220
        "body_temp": 38.5,
    }
    response = client.post("/predict", json=payload, headers=headers)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_predict_inherits_user_profile(client, user_token):
    # normal_user fixture has age=26, gender=female, height=165, weight=60
    headers = {"Authorization": f"Bearer {user_token}"}
    payload = {
        "duration": 20.0,
        "heart_rate": 105.0,
        "body_temp": 38.0,
    }
    response = client.post("/predict", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["predicted_calories"] > 0


def test_predict_extrapolation_warning(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    payload = {
        "duration": 60.0,  # Training set was 1-30 min
        "heart_rate": 110.0,
        "body_temp": 38.2,
    }
    response = client.post("/predict", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["extrapolated"] is True
    assert len(data["warnings"]) > 0
    assert any("duration" in w.lower() for w in data["warnings"])
