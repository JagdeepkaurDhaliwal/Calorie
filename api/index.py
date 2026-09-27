import os
import sys
from pathlib import Path

# Add project root directory to sys.path so app and ml modules resolve cleanly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Set VERCEL environment flag
os.environ.setdefault("VERCEL", "1")

from app.main import app

# Expose app for Vercel Serverless Python runtime
__all__ = ["app"]
