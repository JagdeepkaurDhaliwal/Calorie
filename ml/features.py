from pathlib import Path

import pandas as pd

from ml.config import FEATURE_ORDER, GENDER_FEMALE, GENDER_MALE, RANGES

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "data" / "raw"
HOLDOUT_PATH = ROOT_DIR / "data" / "holdout.csv"


def encode_gender(value) -> int:
    if isinstance(value, (int, float)) and value in (0, 1):
        return int(value)
    text = str(value).strip().lower()
    if text in ("male", "m", "0"):
        return GENDER_MALE
    if text in ("female", "f", "1"):
        return GENDER_FEMALE
    raise ValueError(f"invalid gender: {value}")


def build_features(
    gender,
    age,
    height,
    weight,
    duration,
    heart_rate,
    body_temp,
    meta: dict | None = None,
) -> pd.DataFrame:
    """Return a one-row DataFrame in the saved feature order (unscaled)."""
    order = (meta or {}).get("feature_order") or FEATURE_ORDER
    row = {
        "gender": encode_gender(gender),
        "age": float(age),
        "height": float(height),
        "weight": float(weight),
        "duration": float(duration),
        "heart_rate": float(heart_rate),
        "body_temp": float(body_temp),
    }
    return pd.DataFrame([{col: row[col] for col in order}])


def range_warnings(payload: dict, feature_ranges: dict) -> list[str]:
    mapping = {
        "age": ("age", "years"),
        "height": ("height", "cm"),
        "weight": ("weight", "kg"),
        "duration": ("duration", "min"),
        "heart_rate": ("heart_rate", "bpm"),
        "body_temp": ("body_temp", "C"),
    }
    warnings: list[str] = []
    for key, (unit_key, unit) in mapping.items():
        if key not in feature_ranges or unit_key not in payload or payload[unit_key] is None:
            continue
        lo, hi = feature_ranges[key]
        value = float(payload[unit_key])
        if value < lo or value > hi:
            warnings.append(
                f"{key} {value} {unit} is outside the training range ({lo}-{hi} {unit}); "
                "treat this estimate as approximate"
            )
    return warnings


def api_range_ok(field: str, value: float) -> bool:
    lo, hi = RANGES[field]
    return lo <= value <= hi
