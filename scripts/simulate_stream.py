import argparse
import json
import logging
import random
import sys
import time
from urllib.parse import urlparse

import httpx
try:
    import websockets.sync.client as ws_client
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("simulate_stream")


def main():
    parser = argparse.ArgumentParser(description="Simulate live workout heart-rate stream.")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL of CalorieCast API")
    parser.add_argument("--email", default="alex@example.com", help="User email")
    parser.add_argument("--password", default="Password123!", help="User password")
    parser.add_argument("--readings", type=int, default=12, help="Number of simulated readings")
    parser.add_argument("--interval", type=int, default=1, help="Sleep seconds between readings in simulation")
    parser.add_argument("--mode", choices=["ws", "http"], default="ws", help="Stream protocol: ws or http polling")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    client = httpx.Client(base_url=base_url, timeout=10.0)

    # 1. Login
    logger.info("Logging in as %s...", args.email)
    login_resp = client.post("/auth/login", json={"email": args.email, "password": args.password})
    if login_resp.status_code != 200:
        logger.error("Login failed (%s): %s", login_resp.status_code, login_resp.text)
        sys.exit(1)

    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Start Session
    logger.info("Starting workout session...")
    start_resp = client.post("/sessions/start", json={"body_temp": None}, headers=headers)
    if start_resp.status_code != 201:
        logger.error("Failed to start session (%s): %s", start_resp.status_code, start_resp.text)
        sys.exit(1)

    session_id = start_resp.json()["session_id"]
    logger.info("Started session #%d", session_id)

    # 3. Stream Readings
    hr = 100.0
    if args.mode == "ws" and HAS_WEBSOCKETS:
        parsed = urlparse(base_url)
        ws_scheme = "wss" if parsed.scheme == "https" else "ws"
        ws_url = f"{ws_scheme}://{parsed.netloc}/sessions/{session_id}/stream?token={token}"
        logger.info("Connecting to WebSocket: %s", ws_url)
        with ws_client.connect(ws_url) as ws:
            for i in range(1, args.readings + 1):
                hr += random.uniform(-2, 5)
                hr = max(80.0, min(175.0, hr))
                msg = {"type": "reading", "heart_rate": int(round(hr)), "interval_sec": 5}
                ws.send(json.dumps(msg))
                reply = json.loads(ws.recv())
                logger.info(
                    "Reading %2d/%2d: HR=%d bpm | Elapsed=%ds | Avg HR=%.1f | Burned=%.2f kcal | Intensity=%s",
                    i,
                    args.readings,
                    int(round(hr)),
                    reply.get("elapsed_sec", 0),
                    reply.get("avg_hr", 0.0),
                    reply.get("cumulative_calories", 0.0),
                    reply.get("intensity_so_far", "unknown"),
                )
                time.sleep(args.interval)

            logger.info("Sending session end command...")
            ws.send(json.dumps({"type": "end"}))
            final_summary = json.loads(ws.recv())
            logger.info("Workout Complete! Summary: %s", final_summary)
    else:
        logger.info("Streaming via HTTP polling fallback...")
        for i in range(1, args.readings + 1):
            hr += random.uniform(-2, 5)
            hr = max(80.0, min(175.0, hr))
            reading_resp = client.post(
                f"/sessions/{session_id}/readings",
                json={"heart_rate": int(round(hr)), "interval_sec": 5},
                headers=headers,
            )
            data = reading_resp.json()
            logger.info(
                "Reading %2d/%2d: HR=%d bpm | Elapsed=%ds | Avg HR=%.1f | Burned=%.2f kcal | Intensity=%s",
                i,
                args.readings,
                int(round(hr)),
                data.get("elapsed_sec", 0),
                data.get("avg_hr", 0.0),
                data.get("cumulative_calories", 0.0),
                data.get("intensity_so_far", "unknown"),
            )
            time.sleep(args.interval)

        logger.info("Ending session via HTTP...")
        end_resp = client.post(f"/sessions/{session_id}/end", headers=headers)
        logger.info("Workout Complete! Summary: %s", end_resp.json())


if __name__ == "__main__":
    main()
