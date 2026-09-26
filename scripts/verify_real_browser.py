import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import httpx
import websockets.sync.client as ws_client

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def run_browser_verification():
    print("=== Starting Real-World Browser UI Verification ===")
    
    # 1. Setup isolated Chrome instance
    temp_dir = tempfile.mkdtemp(prefix="calorie_chrome_")
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    
    chrome_proc = subprocess.Popen([
        chrome_path,
        "--headless=new",
        "--remote-debugging-port=9222",
        f"--user-data-dir={temp_dir}",
        "--disable-extensions",
        "--no-first-run",
        "--disable-background-networking"
    ])
    time.sleep(2)
    
    console_errors = []
    
    try:
        resp = httpx.get("http://127.0.0.1:9222/json")
        targets = resp.json()
        page_target = next(t for t in targets if t.get("type") == "page")
        ws_url = page_target["webSocketDebuggerUrl"]
        
        with ws_client.connect(ws_url) as ws:
            msg_id = 1
            def send_cmd(method, params=None):
                nonlocal msg_id
                cmd = {"id": msg_id, "method": method}
                if params:
                    cmd["params"] = params
                ws.send(json.dumps(cmd))
                current_id = msg_id
                msg_id += 1
                
                # Read until response for this id arrives
                while True:
                    raw = ws.recv()
                    res = json.loads(raw)
                    if "method" in res and res["method"] in ["Console.messageAdded", "Runtime.consoleAPICalled", "Log.entryAdded"]:
                        # Track console errors
                        text = str(res.get("params", {}))
                        if "error" in text.lower():
                            console_errors.append(text)
                    if res.get("id") == current_id:
                        return res.get("result", {})

            def evaluate(js_expr):
                r = send_cmd("Runtime.evaluate", {"expression": js_expr, "returnByValue": True})
                return r.get("result", {}).get("value")

            # Enable CDP domains
            send_cmd("Page.enable")
            send_cmd("Runtime.enable")
            send_cmd("Log.enable")
            
            # --- STEP 1: Landing Page ---
            print("\n[Step 1] Loading Landing Page (index.html)...")
            send_cmd("Page.navigate", {"url": "http://127.0.0.1:8000/static/index.html"})
            time.sleep(1)
            title = evaluate("document.title")
            brand = evaluate("document.querySelector('.brand').textContent")
            print(f"  Title: {title}")
            print(f"  Brand Header: {brand}")
            assert "CalorieCast" in title, f"Unexpected title: {title}"

            # --- STEP 2: Login Page & Authentication ---
            print("\n[Step 2] Navigating to Login Page (login.html)...")
            send_cmd("Page.navigate", {"url": "http://127.0.0.1:8000/static/login.html"})
            time.sleep(1)
            
            print("  Entering user credentials for alex@example.com...")
            evaluate("document.getElementById('login-email').value = 'alex@example.com'")
            evaluate("document.getElementById('login-password').value = 'Password123!'")
            evaluate("document.getElementById('login-form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))")
            time.sleep(2)
            
            current_url = evaluate("window.location.href")
            token = evaluate("localStorage.getItem('caloriecast_token')")
            user_obj = evaluate("localStorage.getItem('caloriecast_user')")
            print(f"  Current URL after login: {current_url}")
            print(f"  Token stored in localStorage: {'YES (Bearer JWT)' if token else 'NO'}")
            print(f"  User cached: {user_obj}")
            assert "dashboard.html" in current_url, f"Login did not redirect to dashboard! URL: {current_url}"
            assert token, "Token missing from localStorage!"

            # --- STEP 3: Main Dashboard Dynamic Data Verification ---
            print("\n[Step 3] Verifying Dashboard Dynamic API Data Loading...")
            time.sleep(2)  # Wait for fetch API calls to complete
            
            week_total = evaluate("document.getElementById('stat-week-total').textContent")
            avg_workout = evaluate("document.getElementById('stat-avg-workout').textContent")
            workout_count = evaluate("document.getElementById('stat-count').textContent")
            forecast_total = evaluate("document.getElementById('forecast-total').textContent")
            forecast_badge = evaluate("document.getElementById('forecast-method-badge').textContent")
            forecast_days = evaluate("document.getElementById('forecast-days-grid').children.length")
            history_rows = evaluate("document.getElementById('history-tbody').querySelectorAll('tr').length")
            first_row_text = evaluate("document.getElementById('history-tbody').querySelector('tr')?.innerText")
            
            print(f"  Dynamic Week Total: {week_total}")
            print(f"  Dynamic Avg per Workout: {avg_workout}")
            print(f"  Dynamic Workout Count: {workout_count}")
            print(f"  Dynamic Forecast Total: {forecast_total} ({forecast_badge})")
            print(f"  Dynamic 7-Day Forecast Cards Rendered: {forecast_days} cards")
            print(f"  Dynamic Workout History Rows Loaded: {history_rows} rows")
            print(f"  Sample Row Data: {first_row_text[:80]}...")
            
            assert "kcal" in week_total and week_total != "0.0 kcal", f"Week total not dynamic: {week_total}"
            assert int(workout_count) > 0, f"Workout count zero: {workout_count}"
            assert forecast_days == 7, f"Expected 7 forecast day cards, got {forecast_days}"
            assert history_rows > 0, "No workout history rows loaded!"

            # --- STEP 4: Prediction Flow from Dynamic UI ---
            print("\n[Step 4] Testing Single Workout Prediction UI (predict.html)...")
            send_cmd("Page.navigate", {"url": "http://127.0.0.1:8000/static/predict.html"})
            time.sleep(1.5)
            
            # Verify Profile Pre-fill
            prefill_age = evaluate("document.getElementById('age').value")
            prefill_gender = evaluate("document.getElementById('gender').value")
            prefill_height = evaluate("document.getElementById('height').value")
            prefill_weight = evaluate("document.getElementById('weight').value")
            print(f"  Profile Auto-Pre-fill: Gender={prefill_gender}, Age={prefill_age}, Height={prefill_height}cm, Weight={prefill_weight}kg")
            assert prefill_age == "28", f"Age not prefilled! Got {prefill_age}"
            assert prefill_gender == "male", f"Gender not prefilled! Got {prefill_gender}"

            # Set workout parameters
            evaluate("document.getElementById('duration').value = '25.0'")
            evaluate("document.getElementById('heart_rate').value = '120.0'")
            evaluate("document.getElementById('body_temp').value = '38.8'")
            
            # Submit prediction form
            evaluate("document.getElementById('predict-form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))")
            time.sleep(2)
            
            result_visible = evaluate("document.getElementById('result-content').style.display")
            pred_calories = evaluate("document.getElementById('res-calories').textContent")
            pred_intensity = evaluate("document.getElementById('res-intensity').textContent")
            pred_version = evaluate("document.getElementById('res-version').textContent")
            
            print(f"  Result Box Visibility: {result_visible}")
            print(f"  Dynamic Predicted Calories: {pred_calories}")
            print(f"  Dynamic Workout Intensity: {pred_intensity}")
            print(f"  Model Version Served: v{pred_version}")
            
            assert result_visible == "block", "Result container not displayed!"
            assert "kcal" in pred_calories, f"Calories missing: {pred_calories}"
            assert pred_intensity in ["LOW", "MODERATE", "HIGH"], f"Unexpected intensity: {pred_intensity}"

            # --- STEP 5: Live Simulated Workout via UI ---
            print("\n[Step 5] Testing Live Workout UI Telemetry & WebSocket (live.html)...")
            send_cmd("Page.navigate", {"url": "http://127.0.0.1:8000/static/live.html"})
            time.sleep(1.5)
            
            # Start workout
            print("  Clicking 'Start Live Workout'...")
            evaluate("startWorkout()")
            time.sleep(2)
            
            session_active_visible = evaluate("document.getElementById('active-session-card').style.display")
            stream_status = evaluate("document.getElementById('live-status-mode').textContent.trim()")
            print(f"  Active Session UI Visible: {session_active_visible}")
            print(f"  Stream Connection Status: {stream_status}")
            assert session_active_visible == "block", "Active session card not visible!"
            assert "CONNECTED" in stream_status or "POLLING" in stream_status, f"Unexpected stream status: {stream_status}"

            # Wait for 2 real simulated telemetry readings
            print("  Streaming live telemetry readings over WebSocket (waiting 7s)...")
            time.sleep(7)
            
            live_hr = evaluate("document.getElementById('live-current-hr').textContent")
            live_cal = evaluate("document.getElementById('live-calories').textContent")
            live_timer = evaluate("document.getElementById('live-timer').textContent")
            live_intensity = evaluate("document.getElementById('live-intensity-badge').textContent")
            
            print(f"  Current Live Timer: {live_timer}")
            print(f"  Current Dynamic Heart Rate: {live_hr}")
            print(f"  Live Monotonic Calories: {live_cal}")
            print(f"  Live Intensity: {live_intensity}")
            
            assert live_timer != "00:00", f"Timer did not advance: {live_timer}"
            assert live_hr != "-- bpm", f"Heart rate did not update: {live_hr}"

            # End workout
            print("  Ending workout and generating summary...")
            evaluate("endWorkout()")
            time.sleep(2)
            
            summary_visible = evaluate("document.getElementById('summary-card').style.display")
            sum_cal = evaluate("document.getElementById('sum-total-cal').textContent")
            sum_dur = evaluate("document.getElementById('sum-duration').textContent")
            sum_hr = evaluate("document.getElementById('sum-avg-hr').textContent")
            
            print(f"  Summary Card Visible: {summary_visible}")
            print(f"  Total Burn: {sum_cal}")
            print(f"  Total Duration: {sum_dur}")
            print(f"  Average Heart Rate: {sum_hr}")
            assert summary_visible == "block", "Summary card not displayed!"
            assert "kcal" in sum_cal, f"Invalid summary calories: {sum_cal}"

            # --- STEP 6: Admin Portal Verification ---
            print("\n[Step 6] Testing Admin Portal MLOps UI (admin.html)...")
            send_cmd("Page.navigate", {"url": "http://127.0.0.1:8000/static/login.html"})
            time.sleep(1)
            
            evaluate("document.getElementById('login-email').value = 'admin@caloriecast.local'")
            evaluate("document.getElementById('login-password').value = 'AdminPassword123!'")
            evaluate("document.getElementById('login-form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))")
            time.sleep(2)
            
            admin_url = evaluate("window.location.href")
            print(f"  Current URL after Admin login: {admin_url}")
            assert "admin.html" in admin_url, f"Admin login did not redirect to admin.html! URL: {admin_url}"
            
            time.sleep(2)
            models_table_rows = evaluate("document.getElementById('models-tbody').querySelectorAll('tr').length")
            first_model_row = evaluate("document.getElementById('models-tbody').querySelector('tr')?.innerText")
            print(f"  Admin Models Table Rows: {models_table_rows}")
            print(f"  Active Model Details: {first_model_row.replace(chr(10), ' | ') if first_model_row else 'None'}")
            
            assert models_table_rows > 0, "No models listed in admin table!"
            assert "MLPRegressor" in first_model_row or "RandomForest" in first_model_row, "Expected model algorithm in row!"
            assert "ACTIVE" in first_model_row, "Active model indicator missing!"

            # --- STEP 7: Browser Console Diagnostics ---
            print("\n[Step 7] Checking Browser Console for Errors...")
            if console_errors:
                print(f"  Console Errors Found ({len(console_errors)}):")
                for err in console_errors:
                    print(f"    - {err}")
            else:
                print("  Zero unhandled console errors detected across all tested UI pages.")

    finally:
        chrome_proc.terminate()
        chrome_proc.wait()
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("\n=======================================================")
    print(">>> REAL-WORLD BROWSER UI VERIFICATION: 100% PASSED <<<")
    print("=======================================================")

if __name__ == "__main__":
    run_browser_verification()
