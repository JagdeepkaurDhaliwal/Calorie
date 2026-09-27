import os
import sys
from pathlib import Path

# Ensure VERCEL environment flag is set before any app/config imports
os.environ["VERCEL"] = "1"

# Add project root directory to sys.path so app and ml modules resolve cleanly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app

# Expose both app and handler for maximum compatibility with Vercel ASGI / Serverless runtimes
handler = app
__all__ = ["app", "handler"]

