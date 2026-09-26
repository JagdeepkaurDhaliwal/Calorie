import numpy as np
import pandas as pd
from app.services.forecast_service import ema
from ml.config import FEATURE_ORDER
from ml.features import build_features, encode_gender, range_warnings


def test_gender_encoding():
    assert encode_gender("male") == 0
    assert encode_gender("female") == 1
    assert encode_gender("MALE") == 0
    assert encode_gender("FEMALE") == 1


def test_build_features_order():
    df = build_features(
        gender="female",
        age=30,
        height=165.0,
        weight=60.0,
        duration=25.0,
        heart_rate=120.0,
        body_temp=38.5,
    )
    assert list(df.columns) == FEATURE_ORDER
    assert df["gender"].iloc[0] == 1
    assert df["age"].iloc[0] == 30


def test_range_warnings():
    ranges = {
        "duration": (1.0, 30.0),
        "heart_rate": (60.0, 140.0),
    }
    # Within range
    w1 = range_warnings({"duration": 20.0, "heart_rate": 100.0}, ranges)
    assert len(w1) == 0

    # Outside range
    w2 = range_warnings({"duration": 45.0, "heart_rate": 150.0}, ranges)
    assert len(w2) == 2
    assert any("duration" in msg for msg in w2)
    assert any("heart_rate" in msg for msg in w2)


def test_ema_computation():
    values = [100.0, 120.0, 110.0]
    # alpha = 0.5
    # s1 = 100
    # s2 = 0.5 * 120 + 0.5 * 100 = 110
    # s3 = 0.5 * 110 + 0.5 * 110 = 110
    res = ema(values, alpha=0.5)
    assert res == 110.0
