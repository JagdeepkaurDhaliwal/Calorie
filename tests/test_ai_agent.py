import io


def test_food_image_analysis_and_confirm(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}

    # Upload mock image
    file_content = b"fake-jpeg-image-bytes-salad-bowl"
    files = {"file": ("salad_lunch.jpg", io.BytesIO(file_content), "image/jpeg")}

    res = client.post("/food/analyze-image", files=files, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "analysis_id" in data
    assert data["total_calories"] > 0
    assert len(data["detected_items"]) > 0

    analysis_id = data["analysis_id"]

    # Confirm food analysis into lunch meal
    confirm_payload = {
        "analysis_id": analysis_id,
        "meal_type": "lunch",
        "items": [
            {"food_name": "Mixed Green Garden Salad", "quantity": "1 bowl", "calories": 45.0, "protein": 2.2, "carbs": 8.5, "fat": 0.5}
        ],
    }
    confirm_res = client.post("/food/confirm", json=confirm_payload, headers=headers)
    assert confirm_res.status_code == 201
    meal_data = confirm_res.json()
    assert meal_data["meal_type"] == "lunch"
    assert meal_data["total_calories"] >= 45.0


def test_generate_general_plan(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    res = client.post("/ai/general-plan", headers=headers)
    assert res.status_code == 200
    plan = res.json()
    assert plan["plan_type"] == "general"
    assert "workout_plan" in plan
    assert "nutrition_plan" in plan
    assert "schedule" in plan["workout_plan"]
    assert "disclaimer" in plan["nutrition_plan"]


def test_generate_personalized_plan(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    payload = {
        "goal": "muscle_building",
        "preferred_body_parts": ["chest", "back", "biceps"],
        "dietary_preference": "balanced",
        "workout_days_per_week": 4,
    }
    res = client.post("/ai/personalized-plan", json=payload, headers=headers)
    assert res.status_code == 200
    plan = res.json()
    assert plan["plan_type"] == "personalized"
    assert plan["goal"] == "muscle_building"
    assert plan["daily_calorie_target"] > 0

    # Verify get current plan
    current_res = client.get("/ai/current-plan", headers=headers)
    assert current_res.status_code == 200
    current_plan = current_res.json()
    assert current_plan["id"] == plan["id"]


def test_ai_assistant_chat(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    payload = {"message": "How many calories should I eat to build chest muscle?"}
    res = client.post("/ai/assistant-chat", json=payload, headers=headers)
    assert res.status_code == 200
    chat_res = res.json()
    assert "reply" in chat_res
    assert len(chat_res["suggested_actions"]) > 0
