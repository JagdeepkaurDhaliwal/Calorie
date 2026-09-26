# CalorieCast Mobile App Package

This directory contains the production-ready Android wrapper and configuration for **CalorieCast**.

## Architecture & Options

CalorieCast supports two complementary mobile modes:

### 1. Progressive Web App (PWA) — Zero Setup
- **Instant Installation:** Open `http://localhost:8000/static/dashboard.html` in Chrome or Edge on desktop or mobile.
- Tap **"Install App"** from the banner or browser menu (⋮) -> **"Add to Home screen"**.
- Runs in standalone fullscreen mode without browser URL bars, with full offline caching via Service Worker (`/sw.js`) and Web App Manifest (`/manifest.json`).

### 2. Pre-Built APK (Ready to Install)
The APK has already been compiled and signed in debug mode:
- **APK Location:** `D:\Calorie\CalorieCast.apk` (Size: 5.37 MB)
- **Install on Device via ADB:**
  ```powershell
  D:\AndroidTools\sdk\platform-tools\adb.exe install -r D:\Calorie\CalorieCast.apk
  ```
- **Direct Phone Install:** Copy `CalorieCast.apk` to phone storage or download via phone browser, tap the file, and select **Install**.

### 3. Native Android App (Source Project)
The project in `android/` can be opened directly in **Android Studio** or built autonomously via command line:
- **Package Name:** `com.caloriecast.app`
- **Target SDK:** Android 14 (API 34)
- **Min SDK:** Android 6.0 (API 23)
- **Toolchain (on D:\ drive):**
  - JDK: `D:\AndroidTools\jdk-17`
  - Android SDK: `D:\AndroidTools\sdk`
  - Gradle: `D:\AndroidTools\gradle-8.5`
- **Rebuilding APK from Command Line:**
  ```powershell
  python D:\Calorie\scripts\setup_android_sdk.py
  ```
- **Features:**
  - Hardware accelerated WebView
  - Camera & Gallery file chooser for the **AI Food Calorie Image Scanner**
  - Native Back button stack handling
  - WebSocket support for **Live Workout Telemetry**
  - Dark mode status bar integration

### How to Open & Run in Android Studio:
1. Open Android Studio -> Select **Open an Existing Project** -> Choose `D:\Calorie\android`.
2. Android Studio will automatically pick up `D:\Calorie\android\local.properties`.
3. Connect an Android phone via USB (with Developer Mode & USB Debugging enabled) or start an Android Virtual Device (AVD).
4. Click **Run 'app'** (Shift + F10).
5. The app connects to your local machine at `http://10.0.2.2:8000` (in emulator) or your local network IP (on physical device).

