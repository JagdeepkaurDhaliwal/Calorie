import os
import requests

BASE_URL = "http://127.0.0.1:8000"

def verify_mobile():
    print("=== VERIFYING MOBILE APP & PWA MIGRATION ===")

    # 1. Manifest
    res = requests.get(f"{BASE_URL}/manifest.json")
    assert res.status_code == 200, f"Manifest failed: {res.status_code}"
    manifest = res.json()
    assert manifest["display"] == "standalone"
    assert len(manifest["icons"]) >= 3
    print(f"[OK] Web App Manifest OK: Name='{manifest['name']}', Display={manifest['display']}, Icons={len(manifest['icons'])}")

    # 2. Service Worker
    sw_res = requests.get(f"{BASE_URL}/sw.js")
    assert sw_res.status_code == 200, f"SW failed: {sw_res.status_code}"
    assert "Service-Worker-Allowed" in sw_res.headers
    assert sw_res.headers["Service-Worker-Allowed"] == "/"
    print("[OK] Service Worker Route OK: Headers have Service-Worker-Allowed: /")

    # 3. Favicon & Icons
    fav_res = requests.get(f"{BASE_URL}/favicon.ico")
    assert fav_res.status_code == 200, f"Favicon failed: {fav_res.status_code}"
    print(f"[OK] Favicon OK: Content-Type={fav_res.headers.get('Content-Type')}")

    for ic in ["icon-192.png", "icon-512.png", "icon-maskable.png"]:
        ic_res = requests.get(f"{BASE_URL}/static/icons/{ic}")
        assert ic_res.status_code == 200, f"Icon {ic} failed: {ic_res.status_code}"
    print("[OK] High-Res Icons (192, 512, maskable) verified.")

    # 4. Check HTML integration
    pages = [
        "/static/dashboard.html",
        "/static/workouts.html",
        "/static/nutrition.html",
        "/static/ai_agent.html",
        "/static/live.html",
        "/static/predict.html",
        "/static/index.html",
    ]
    for p in pages:
        page_res = requests.get(f"{BASE_URL}{p}")
        assert page_res.status_code == 200
        text = page_res.text
        assert 'rel="manifest"' in text, f"Missing manifest link in {p}"
        assert 'pwa.js' in text, f"Missing pwa.js script in {p}"
        assert 'viewport-fit=cover' in text, f"Missing mobile viewport in {p}"
    print(f"[OK] All {len(pages)} HTML pages configured with mobile viewport, manifest, and PWA controller.")

    # 5. Android Package Files
    root_dir = os.path.dirname(os.path.dirname(__file__))
    android_files = [
        "android/app/src/main/AndroidManifest.xml",
        "android/app/src/main/java/com/caloriecast/app/MainActivity.java",
        "android/app/build.gradle",
        "android/build.gradle",
        "android/settings.gradle",
        "android/capacitor.config.json",
        "android/README.md",
    ]
    for af in android_files:
        full_p = os.path.join(root_dir, af)
        assert os.path.exists(full_p), f"Missing Android file: {af}"
    print(f"[OK] All {len(android_files)} Native Android package files verified on disk.")

    print("\nSUCCESS: MOBILE APP & PWA MIGRATION FULLY VERIFIED 100%!")

if __name__ == "__main__":
    verify_mobile()
