import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def run_e2e():
    print("=== STARTING CALORIECAST E2E VERIFICATION ===")

    # 1. Health check
    res = requests.get(f"{BASE_URL}/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("[OK] Health Check OK:", res.json())

    # 2. Register/Login user
    email = "athlete_e2e@example.com"
    pwd = "Password123!"
    # Register if needed
    requests.post(f"{BASE_URL}/auth/register", json={"name": "Alex Athlete", "email": email, "password": pwd})
    
    # Login
    login_res = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Login successful, token acquired.")

    # 3. Exercises & Body Parts
    bp_res = requests.get(f"{BASE_URL}/exercises/body-parts", headers=headers)
    assert bp_res.status_code == 200
    parts = bp_res.json()
    assert len(parts) >= 7
    print(f"[OK] Standard Body Parts ({len(parts)}): {[p['id'] for p in parts]}")

    ex_res = requests.get(f"{BASE_URL}/exercises", headers=headers)
    assert ex_res.status_code == 200
    exercises = ex_res.json()
    assert len(exercises) >= 20
    print(f"[OK] Exercise Catalogue Loaded ({len(exercises)} exercises).")

    # 4. Log Strength Exercise for Chest
    bench_payload = {
        "exercise_name": "Bench Press",
        "exercise_type": "strength",
        "body_part": "chest",
        "sets": 4,
        "reps": 10,
        "weight_kg": 65.0,
        "duration_min": 25.0,
        "intensity": "moderate",
    }
    log_res = requests.post(f"{BASE_URL}/exercises/workout", json=bench_payload, headers=headers)
    assert log_res.status_code == 201
    bench_data = log_res.json()
    print(f"[OK] Logged Chest Bench Press: {bench_data['calories_burned']} kcal burned.")

    # 5. Log Cardio Exercise for Legs
    run_payload = {
        "exercise_name": "Treadmill Running",
        "exercise_type": "cardio",
        "body_part": "legs",
        "duration_min": 30.0,
        "heart_rate": 145.0,
        "intensity": "high",
    }
    cardio_res = requests.post(f"{BASE_URL}/exercises/workout", json=run_payload, headers=headers)
    assert cardio_res.status_code == 201
    cardio_data = cardio_res.json()
    print(f"[OK] Logged Legs Treadmill Run: {cardio_data['calories_burned']} kcal burned.")

    # 6. Verify Today's Body Calorie Map
    map_res = requests.get(f"{BASE_URL}/workouts/body-part-summary", headers=headers)
    assert map_res.status_code == 200
    map_data = map_res.json()
    chest_cals = map_data["body_parts"]["chest"]
    legs_cals = map_data["body_parts"]["legs"]
    assert chest_cals > 0
    assert legs_cals > 0
    print(f"[OK] Today's Body Calorie Map OK: Chest={chest_cals} kcal, Legs={legs_cals} kcal, Total={map_data['total_exercise_calories']} kcal.")

    # 7. Nutrition & Meal Tracking
    nut_today = requests.get(f"{BASE_URL}/nutrition/today", headers=headers).json()
    print(f"[OK] Daily Nutrition Target: {nut_today['daily_target']} kcal, Burned: {nut_today['exercise_calories']} kcal, Status: {nut_today['status_message']}")

    # Log Breakfast
    meal_payload = {
        "meal_type": "breakfast",
        "items": [
            {"food_name": "Rolled Oatmeal (Cooked)", "quantity": "1 bowl", "calories": 158.0, "protein": 5.9, "carbs": 27.0, "fat": 3.2},
            {"food_name": "Whole Boiled Egg", "quantity": "2 eggs", "calories": 156.0, "protein": 12.6, "carbs": 1.2, "fat": 10.6}
        ]
    }
    meal_res = requests.post(f"{BASE_URL}/nutrition/meals", json=meal_payload, headers=headers)
    assert meal_res.status_code == 201
    print(f"[OK] Logged Breakfast: {meal_res.json()['total_calories']} kcal.")

    # 8. AI Food Image Analysis & Confirmation
    img_bytes = b"sample-food-photo-chicken-salad"
    files = {"file": ("grilled_chicken_plate.jpg", img_bytes, "image/jpeg")}
    ai_img_res = requests.post(f"{BASE_URL}/food/analyze-image", files=files, headers=headers)
    assert ai_img_res.status_code == 200
    ai_img_data = ai_img_res.json()
    print(f"[OK] AI Food Image Analysis: Detected {len(ai_img_data['detected_items'])} items, ~{ai_img_data['total_calories']} kcal.")

    confirm_payload = {
        "analysis_id": ai_img_data["analysis_id"],
        "meal_type": "lunch",
        "items": [
            {"food_name": "Grilled Chicken Breast", "quantity": "150g", "calories": 248.0, "protein": 46.5, "carbs": 0.0, "fat": 5.4}
        ]
    }
    conf_res = requests.post(f"{BASE_URL}/food/confirm", json=confirm_payload, headers=headers)
    assert conf_res.status_code == 201
    print(f"[OK] Confirmed AI Analysis to Lunch: {conf_res.json()['total_calories']} kcal.")

    # 9. Smart Food Recommendations
    recs_res = requests.get(f"{BASE_URL}/nutrition/recommendations", headers=headers)
    assert recs_res.status_code == 200
    recs = recs_res.json()
    print(f"[OK] Smart Recommendations ({len(recs)}): {[r['food_name'] for r in recs]}")

    # 10. Mode 1: General AI Plan
    g_plan = requests.post(f"{BASE_URL}/ai/general-plan", headers=headers).json()
    assert g_plan["plan_type"] == "general"
    print(f"[OK] Mode 1 Plan Generated: '{g_plan['title']}' ({len(g_plan['workout_plan']['schedule'])} days)")

    # 11. Mode 2: Personalized AI Plan
    p_req = {
        "goal": "muscle_building",
        "preferred_body_parts": ["chest", "back", "legs"],
        "dietary_preference": "high_protein_nonveg",
        "workout_days_per_week": 4
    }
    p_plan = requests.post(f"{BASE_URL}/ai/personalized-plan", json=p_req, headers=headers).json()
    assert p_plan["plan_type"] == "personalized"
    print(f"[OK] Mode 2 Plan Generated: '{p_plan['title']}', Target: {p_plan['daily_calorie_target']} kcal/day.")

    # 12. AI Chat Assistant
    chat_res = requests.post(f"{BASE_URL}/ai/assistant-chat", json={"message": "How to maximize chest hypertrophy?"}, headers=headers).json()
    print(f"[OK] AI Chat Assistant OK: Reply preview: '{chat_res['reply'][:60]}...'")

    # 13. Flexible Predict
    pred_res = requests.post(f"{BASE_URL}/predict", json={"duration": 35.0, "heart_rate": 130.0, "body_temp": 38.5, "gender": "male", "age": 28, "height": 178.0, "weight": 75.0}, headers=headers).json()
    print(f"[OK] Quick Predict OK: {pred_res['predicted_calories']} kcal, Intensity: {pred_res['intensity']}.")

    # 14. Frontend HTML Pages Verification
    pages = [
        "/static/index.html",
        "/static/dashboard.html",
        "/static/workouts.html",
        "/static/nutrition.html",
        "/static/ai_agent.html",
        "/static/live.html",
        "/static/predict.html",
        "/static/login.html",
        "/static/admin.html",
        "/static/js/body_map.js",
        "/static/css/style.css",
    ]
    for p in pages:
        page_res = requests.get(f"{BASE_URL}{p}")
        assert page_res.status_code == 200, f"Page failed: {p} ({page_res.status_code})"
    print(f"[OK] All {len(pages)} Frontend HTML/JS/CSS assets verified HTTP 200.")

    print("\nSUCCESS: ALL REAL-WORLD E2E VERIFICATIONS PASSED 100%!")

if __name__ == "__main__":
    run_e2e()
