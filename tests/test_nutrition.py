def test_get_food_catalogue(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    res = client.get("/nutrition/food-items", headers=headers)
    assert res.status_code == 200
    foods = res.json()
    assert len(foods) >= 15
    names = [f["name"] for f in foods]
    assert any("Rice" in n for n in names)
    assert any("Dal" in n for n in names)
    assert any("Roti" in n for n in names)


def test_log_meal_and_daily_summary(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}

    # Log breakfast
    meal_payload = {
        "meal_type": "breakfast",
        "items": [
            {"food_name": "Whole Boiled Egg", "quantity": "2 large", "calories": 156.0, "protein": 12.6, "carbs": 1.2, "fat": 10.6},
            {"food_name": "Whole Wheat Bread", "quantity": "2 slices", "calories": 160.0, "protein": 6.0, "carbs": 28.0, "fat": 2.0},
        ],
    }
    res = client.post("/nutrition/meals", json=meal_payload, headers=headers)
    assert res.status_code == 201
    meal_data = res.json()
    assert meal_data["meal_type"] == "breakfast"
    assert meal_data["total_calories"] == 316.0
    assert len(meal_data["items"]) == 2

    # Query daily nutrition
    summary_res = client.get("/nutrition/today", headers=headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["consumed_calories"] >= 316.0
    assert summary["daily_target"] > 0
    assert summary["remaining_calories"] == round(summary["daily_target"] - summary["consumed_calories"], 1)
    assert summary["meals"]["breakfast"] is not None


def test_food_recommendations(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    res = client.get("/nutrition/recommendations", headers=headers)
    assert res.status_code == 200
    recs = res.json()
    assert isinstance(recs, list)
    assert len(recs) >= 1
    assert "food_name" in recs[0]
    assert "calories" in recs[0]
    assert "protein" in recs[0]
    assert "reason" in recs[0]
