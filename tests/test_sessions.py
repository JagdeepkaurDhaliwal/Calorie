def test_tc9_and_tc10_session_lifecycle(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}

    # 1. Start session
    start_resp = client.post("/sessions/start", json={"body_temp": 38.0}, headers=headers)
    assert start_resp.status_code == 201
    session_id = start_resp.json()["session_id"]

    # Starting a second active session should raise 409 Conflict
    conflict_resp = client.post("/sessions/start", json={"body_temp": None}, headers=headers)
    assert conflict_resp.status_code == 409

    # 2. Add readings (TC-9: cumulative calories rise monotonically)
    r1 = client.post(f"/sessions/{session_id}/readings", json={"heart_rate": 110, "interval_sec": 5}, headers=headers)
    assert r1.status_code == 200
    cal1 = r1.json()["cumulative_calories"]
    assert cal1 >= 0

    r2 = client.post(f"/sessions/{session_id}/readings", json={"heart_rate": 125, "interval_sec": 5}, headers=headers)
    assert r2.status_code == 200
    cal2 = r2.json()["cumulative_calories"]
    assert cal2 >= cal1  # Monotonic increase

    # 3. End session
    end_resp = client.post(f"/sessions/{session_id}/end", headers=headers)
    assert end_resp.status_code == 200
    summary = end_resp.json()
    assert summary["total_calories"] >= cal2
    assert summary["workout_id"] is not None

    # 4. TC-10: Post reading on ended session must fail with 409 Conflict
    r_after = client.post(f"/sessions/{session_id}/readings", json={"heart_rate": 120, "interval_sec": 5}, headers=headers)
    assert r_after.status_code == 409
    assert r_after.json()["error"]["code"] == "CONFLICT"


def test_session_websocket_stream(client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    start_resp = client.post("/sessions/start", json={"body_temp": None}, headers=headers)
    assert start_resp.status_code == 201
    session_id = start_resp.json()["session_id"]

    # Connect to WebSocket
    with client.websocket_connect(f"/sessions/{session_id}/stream?token={user_token}") as ws:
        # Send reading
        ws.send_json({"type": "reading", "heart_rate": 120, "interval_sec": 5})
        reply = ws.receive_json()
        assert reply["type"] == "update"
        assert reply["cumulative_calories"] >= 0
        assert reply["avg_hr"] == 120.0

        # Send invalid reading
        ws.send_json({"type": "reading", "heart_rate": 500, "interval_sec": 5})
        err_reply = ws.receive_json()
        assert err_reply["type"] == "error"
        assert err_reply["code"] == "INVALID_READING"

        # End session
        ws.send_json({"type": "end"})
        summary_reply = ws.receive_json()
        assert summary_reply["type"] == "summary"
        assert summary_reply["total_calories"] >= 0
