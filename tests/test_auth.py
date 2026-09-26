def test_tc1_register_valid(client):
    payload = {
        "name": "Jane Doe",
        "email": "janedoe@example.com",
        "password": "SecurePassword123!",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "janedoe@example.com"
    assert data["name"] == "Jane Doe"
    assert data["role"] == "user"
    assert "id" in data


def test_tc2_register_duplicate_email(client, normal_user):
    payload = {
        "name": "Duplicate User",
        "email": normal_user.email,
        "password": "Password123!",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data["error"]["code"] == "CONFLICT"


def test_tc3_login_wrong_password(client, normal_user):
    payload = {
        "email": normal_user.email,
        "password": "WrongPassword999!",
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"


def test_login_success(client, normal_user):
    payload = {
        "email": normal_user.email,
        "password": "Password123!",
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_tc4_access_without_token(client):
    response = client.get("/workouts")
    assert response.status_code == 401


def test_tc11_admin_route_as_normal_user(client, user_token):
    response = client.get("/admin/models", headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "FORBIDDEN"


def test_user_get_and_update_profile(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    resp = client.get("/users/me", headers=headers)
    assert resp.status_code == 200
    user_data = resp.json()
    assert user_data["age"] == 26

    # Update profile
    update_resp = client.put("/users/me", json={"age": 27, "weight_kg": 59.5}, headers=headers)
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["age"] == 27
    assert updated["weight_kg"] == 59.5
