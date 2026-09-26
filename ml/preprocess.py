from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from ml.config import FEATURE_ORDER, HOLDOUT_FRACTION, RANDOM_STATE, RANGES
from ml.features import HOLDOUT_PATH, RAW_DIR, encode_gender


REQUIRED_MERGED_COLUMNS = [
    "Gender",
    "Age",
    "Height",
    "Weight",
    "Duration",
    "Heart_Rate",
    "Body_Temp",
    "Calories",
]


def generate_synthetic_raw(n: int = 8000, seed: int = RANDOM_STATE) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create Kaggle-shaped CSVs when the public files are not present."""
    rng = np.random.default_rng(seed)
    user_ids = np.arange(1, n + 1)
    gender = rng.choice(["male", "female"], size=n)
    age = rng.integers(20, 80, size=n)
    height = np.where(gender == "male", rng.normal(175, 8, n), rng.normal(162, 7, n))
    height = np.clip(height, 140, 210)
    weight = np.where(gender == "male", rng.normal(78, 12, n), rng.normal(64, 10, n))
    weight = np.clip(weight, 40, 140)
    duration = rng.integers(1, 31, size=n).astype(float)
    heart_rate = rng.normal(95, 12, n)
    heart_rate = np.clip(heart_rate, 67, 128)
    body_temp = 37.1 + duration * 0.08 + (heart_rate - 90) * 0.01 + rng.normal(0, 0.15, n)
    body_temp = np.clip(body_temp, 37.1, 41.5)

    gender_factor = np.where(gender == "male", 1.0, 0.92)
    calories = (
        duration
        * (
            0.55
            + 0.045 * (heart_rate - 60)
            + 0.8 * (body_temp - 37)
            + 0.004 * (weight - 70)
            - 0.002 * (age - 40)
        )
        * gender_factor
    )
    calories = calories + rng.normal(0, 1.2, n)
    calories = np.clip(calories, 1.0, None)

    exercise = pd.DataFrame(
        {
            "User_ID": user_ids,
            "Gender": gender,
            "Age": age,
            "Height": height.round(1),
            "Weight": weight.round(1),
            "Duration": duration,
            "Heart_Rate": heart_rate.round(1),
            "Body_Temp": body_temp.round(2),
        }
    )
    calories_df = pd.DataFrame({"User_ID": user_ids, "Calories": calories.round(1)})
    return exercise, calories_df


def ensure_raw_csvs() -> tuple[Path, Path]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    exercise_path = RAW_DIR / "exercise.csv"
    calories_path = RAW_DIR / "calories.csv"
    if exercise_path.exists() and calories_path.exists():
        return exercise_path, calories_path
    exercise, calories = generate_synthetic_raw()
    exercise.to_csv(exercise_path, index=False)
    calories.to_csv(calories_path, index=False)
    return exercise_path, calories_path


def load_merged(exercise_path: Path | None = None, calories_path: Path | None = None) -> pd.DataFrame:
    if exercise_path is None or calories_path is None:
        exercise_path, calories_path = ensure_raw_csvs()
    exercise = pd.read_csv(exercise_path)
    calories = pd.read_csv(calories_path)
    df = exercise.merge(calories, on="User_ID", how="inner")
    return df


def clean_merged(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_MERGED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}")
    out = df[REQUIRED_MERGED_COLUMNS].copy()
    out = out.drop_duplicates()
    numeric_cols = ["Age", "Height", "Weight", "Duration", "Heart_Rate", "Body_Temp", "Calories"]
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=numeric_cols + ["Gender"])
    rename = {
        "Gender": "gender",
        "Age": "age",
        "Height": "height",
        "Weight": "weight",
        "Duration": "duration",
        "Heart_Rate": "heart_rate",
        "Body_Temp": "body_temp",
        "Calories": "calories",
    }
    out = out.rename(columns=rename)
    out["gender"] = out["gender"].map(encode_gender)
    for field, (lo, hi) in RANGES.items():
        if field in out.columns:
            out = out[(out[field] >= lo) & (out[field] <= hi)]
    out = out[FEATURE_ORDER + ["calories"]].reset_index(drop=True)
    return out


def split_holdout(df: pd.DataFrame, holdout_path: Path = HOLDOUT_PATH) -> tuple[pd.DataFrame, pd.DataFrame]:
    holdout_path.parent.mkdir(parents=True, exist_ok=True)
    if holdout_path.exists():
        holdout = pd.read_csv(holdout_path)
        key_cols = FEATURE_ORDER + ["calories"]
        train = _anti_join(df, holdout, key_cols)
        if train.empty:
            train, holdout = train_test_split(
                df, test_size=HOLDOUT_FRACTION, random_state=RANDOM_STATE
            )
        return train.reset_index(drop=True), holdout.reset_index(drop=True)

    train, holdout = train_test_split(df, test_size=HOLDOUT_FRACTION, random_state=RANDOM_STATE)
    holdout.to_csv(holdout_path, index=False)
    return train.reset_index(drop=True), holdout.reset_index(drop=True)


def _anti_join(left: pd.DataFrame, right: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    merged = left.merge(right[cols].drop_duplicates(), on=cols, how="left", indicator=True)
    return merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])


def load_upload_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Accept either Kaggle-style names or already-cleaned names.
    aliases = {
        "gender": "Gender",
        "age": "Age",
        "height": "Height",
        "weight": "Weight",
        "duration": "Duration",
        "heart_rate": "Heart_Rate",
        "body_temp": "Body_Temp",
        "calories": "Calories",
    }
    for src, dest in aliases.items():
        if src in df.columns and dest not in df.columns:
            df = df.rename(columns={src: dest})
    if "User_ID" not in df.columns:
        df["User_ID"] = np.arange(1, len(df) + 1)
    if "Calories" not in df.columns:
        raise ValueError("uploaded CSV must include Calories")
    return clean_merged(df)
