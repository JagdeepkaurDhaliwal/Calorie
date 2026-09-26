import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

BASE_DIR = r"D:\AndroidTools"
TMP_DIR = r"D:\tmp"
JDK_DIR = os.path.join(BASE_DIR, "jdk-17")
SDK_DIR = os.path.join(BASE_DIR, "sdk")
GRADLE_DIR = os.path.join(BASE_DIR, "gradle-8.5")

JDK_URL = "https://aka.ms/download-jdk/microsoft-jdk-17.0.10-windows-x64.zip"
CMDLINE_TOOLS_URL = "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
GRADLE_URL = "https://services.gradle.org/distributions/gradle-8.5-bin.zip"


def log(msg: str):
    print(f"[AndroidBuilder] {msg}", flush=True)


def download_file(url: str, dest_path: str):
    if os.path.exists(dest_path):
        log(f"Archive already downloaded at {dest_path}")
        return
    log(f"Downloading from {url}...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response, open(dest_path, 'wb') as out_file:
        total = int(response.info().get('Content-Length', 0))
        downloaded = 0
        chunk_size = 1024 * 1024  # 1MB
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            if total > 0:
                pct = (downloaded / total) * 100
                print(f"\rDownloading: {downloaded / (1024*1024):.1f} MB / {total / (1024*1024):.1f} MB ({pct:.1f}%)", end="", flush=True)
    print()
    log(f"Saved to {dest_path}")


def extract_zip(zip_path: str, extract_to: str):
    log(f"Extracting {zip_path} to {extract_to}...")
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(extract_to)
    log(f"Extracted to {extract_to}")


def setup_jdk() -> str:
    java_exe = os.path.join(JDK_DIR, "bin", "java.exe")
    if os.path.exists(java_exe):
        log(f"Java already installed at {JDK_DIR}")
        return JDK_DIR

    os.makedirs(TMP_DIR, exist_ok=True)
    os.makedirs(BASE_DIR, exist_ok=True)

    zip_path = os.path.join(TMP_DIR, "jdk17.zip")
    download_file(JDK_URL, zip_path)

    temp_extract = os.path.join(TMP_DIR, "jdk_extract")
    os.makedirs(temp_extract, exist_ok=True)
    extract_zip(zip_path, temp_extract)

    # Find inner folder
    subdirs = [os.path.join(temp_extract, d) for d in os.listdir(temp_extract) if os.path.isdir(os.path.join(temp_extract, d))]
    source_dir = subdirs[0] if subdirs else temp_extract
    if os.path.exists(JDK_DIR):
        shutil.rmtree(JDK_DIR)
    shutil.move(source_dir, JDK_DIR)
    shutil.rmtree(temp_extract, ignore_errors=True)

    log(f"JDK installed successfully at {JDK_DIR}")
    return JDK_DIR


def setup_cmdline_tools() -> str:
    sdkmanager_bat = os.path.join(SDK_DIR, "cmdline-tools", "latest", "bin", "sdkmanager.bat")
    if os.path.exists(sdkmanager_bat):
        log(f"Android cmdline-tools already installed at {sdkmanager_bat}")
        return SDK_DIR

    os.makedirs(TMP_DIR, exist_ok=True)
    zip_path = os.path.join(TMP_DIR, "cmdline_tools.zip")
    download_file(CMDLINE_TOOLS_URL, zip_path)

    temp_extract = os.path.join(TMP_DIR, "cmdline_extract")
    os.makedirs(temp_extract, exist_ok=True)
    extract_zip(zip_path, temp_extract)

    target_latest = os.path.join(SDK_DIR, "cmdline-tools", "latest")
    os.makedirs(os.path.dirname(target_latest), exist_ok=True)
    if os.path.exists(target_latest):
        shutil.rmtree(target_latest)

    # Inner cmdline-tools folder
    inner_tools = os.path.join(temp_extract, "cmdline-tools")
    if os.path.exists(inner_tools):
        shutil.move(inner_tools, target_latest)
    else:
        shutil.move(temp_extract, target_latest)

    shutil.rmtree(temp_extract, ignore_errors=True)
    log(f"Android cmdline-tools installed at {target_latest}")
    return SDK_DIR


def setup_gradle() -> str:
    gradle_bat = os.path.join(GRADLE_DIR, "bin", "gradle.bat")
    if os.path.exists(gradle_bat):
        log(f"Gradle already installed at {gradle_bat}")
        return GRADLE_DIR

    os.makedirs(TMP_DIR, exist_ok=True)
    zip_path = os.path.join(TMP_DIR, "gradle85.zip")
    download_file(GRADLE_URL, zip_path)

    temp_extract = os.path.join(TMP_DIR, "gradle_extract")
    os.makedirs(temp_extract, exist_ok=True)
    extract_zip(zip_path, temp_extract)

    subdirs = [os.path.join(temp_extract, d) for d in os.listdir(temp_extract) if os.path.isdir(os.path.join(temp_extract, d))]
    source_dir = subdirs[0] if subdirs else temp_extract
    if os.path.exists(GRADLE_DIR):
        shutil.rmtree(GRADLE_DIR)
    shutil.move(source_dir, GRADLE_DIR)
    shutil.rmtree(temp_extract, ignore_errors=True)

    log(f"Gradle installed successfully at {GRADLE_DIR}")
    return GRADLE_DIR


def install_android_packages(jdk_path: str, sdk_path: str):
    env = os.environ.copy()
    env["JAVA_HOME"] = jdk_path
    env["ANDROID_HOME"] = sdk_path
    env["ANDROID_SDK_ROOT"] = sdk_path
    env["PATH"] = f"{jdk_path}\\bin;{sdk_path}\\cmdline-tools\\latest\\bin;{sdk_path}\\platform-tools;{env.get('PATH', '')}"

    sdkmanager = os.path.join(sdk_path, "cmdline-tools", "latest", "bin", "sdkmanager.bat")

    # 1. Accept licenses
    log("Accepting Android SDK licenses...")
    license_proc = subprocess.Popen(
        [sdkmanager, "--licenses"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    license_proc.communicate(input="y\ny\ny\ny\ny\ny\ny\ny\ny\n")

    # 2. Install platforms and build-tools
    log("Installing Android platforms;android-34 and build-tools;34.0.0...")
    pkgs = ["platform-tools", "platforms;android-34", "build-tools;34.0.0"]
    install_proc = subprocess.run(
        [sdkmanager] + pkgs,
        input="y\ny\ny\n",
        text=True,
        env=env,
        capture_output=True,
    )
    if install_proc.returncode != 0:
        log(f"sdkmanager output: {install_proc.stdout}\nError: {install_proc.stderr}")
    else:
        log("Android platforms and build-tools installed successfully!")


def build_apk(jdk_path: str, sdk_path: str, gradle_path: str):
    android_project = r"D:\Calorie\android"

    # Write local.properties
    local_props = os.path.join(android_project, "local.properties")
    escaped_sdk = sdk_path.replace("\\", "\\\\")
    with open(local_props, "w") as f:
        f.write(f"sdk.dir={escaped_sdk}\n")
    log(f"Wrote local.properties pointing to {sdk_path}")

    # Build environment
    env = os.environ.copy()
    env["JAVA_HOME"] = jdk_path
    env["ANDROID_HOME"] = sdk_path
    env["ANDROID_SDK_ROOT"] = sdk_path
    env["GRADLE_USER_HOME"] = r"D:\tmp\gradle_user"
    env["PATH"] = f"{jdk_path}\\bin;{gradle_path}\\bin;{sdk_path}\\cmdline-tools\\latest\\bin;{env.get('PATH', '')}"

    # Sync frontend into Android assets so APK is completely self-contained and instant offline
    frontend_dir = r"D:\Calorie\frontend"
    assets_static = os.path.join(android_project, "app", "src", "main", "assets", "static")
    if os.path.exists(frontend_dir):
        if os.path.exists(assets_static):
            shutil.rmtree(assets_static)
        shutil.copytree(frontend_dir, assets_static)
        log(f"Synchronized frontend assets to {assets_static}")

    gradle_bat = os.path.join(gradle_path, "bin", "gradle.bat")
    log("Executing gradle assembleDebug...")

    res = subprocess.run(
        [gradle_bat, "assembleDebug", "--stacktrace"],
        cwd=android_project,
        env=env,
        capture_output=True,
        text=True,
    )

    log(f"Gradle stdout:\n{res.stdout[-2000:] if len(res.stdout) > 2000 else res.stdout}")
    if res.returncode != 0:
        log(f"Gradle build failed with returncode {res.returncode}:\n{res.stderr[-2000:] if len(res.stderr) > 2000 else res.stderr}")
        return False

    apk_source = os.path.join(android_project, "app", "build", "outputs", "apk", "debug", "app-debug.apk")
    if os.path.exists(apk_source):
        apk_dest = r"D:\Calorie\CalorieCast.apk"
        shutil.copy2(apk_source, apk_dest)
        size_mb = os.path.getsize(apk_dest) / (1024 * 1024)
        log(f"SUCCESS! APK built and copied to {apk_dest} ({size_mb:.2f} MB)")
        return True
    else:
        log(f"Could not locate generated APK at {apk_source}")
        return False


def main():
    log("Starting autonomous Android SDK setup & APK compilation...")
    jdk = setup_jdk()
    sdk = setup_cmdline_tools()
    gradle = setup_gradle()
    install_android_packages(jdk, sdk)
    success = build_apk(jdk, sdk, gradle)
    if success:
        log("APK Build Completed Successfully!")
    else:
        log("APK Build encountered issues. Check logs above.")


if __name__ == "__main__":
    main()
