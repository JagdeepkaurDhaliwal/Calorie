from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml.features import build_features, range_warnings

logger = logging.getLogger(__name__)


@dataclass
class LoadedModel:
    version_id: int
    regressor: object
    classifier: object
    scaler: object
    temp_model: object
    meta: dict
    keras_regressor: bool = False

    def regressor_predict(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        scaled = self.scaler.transform(X)
        preds = self.regressor.predict(scaled)
        return np.asarray(preds).reshape(-1)

    def classify(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        scaled = self.scaler.transform(X)
        return np.asarray(self.classifier.predict(scaled)).reshape(-1)

    def estimate_body_temp(self, duration: float, heart_rate: float) -> float:
        pred = self.temp_model.predict([[duration, heart_rate]])[0]
        return float(pred)

    def range_warnings_for(self, payload: dict) -> list[str]:
        return range_warnings(payload, self.meta.get("feature_ranges") or {})


class ModelRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded: LoadedModel | None = None

    def active(self) -> LoadedModel:
        with self._lock:
            if self._loaded is None:
                raise RuntimeError("No active model is loaded")
            return self._loaded

    def has_active(self) -> bool:
        with self._lock:
            return self._loaded is not None

    def reload(self, version_id: int, artifact_dir: str | Path) -> None:
        loaded = load_bundle(version_id, Path(artifact_dir))
        with self._lock:
            self._loaded = loaded
        logger.info("Loaded model version %s from %s", version_id, artifact_dir)

    def try_reload(self, version_id: int, artifact_dir: str | Path) -> bool:
        try:
            self.reload(version_id, artifact_dir)
            return True
        except Exception:
            logger.exception("Failed to load model version %s", version_id)
            return False


def load_bundle(version_id: int, artifact_dir: Path) -> LoadedModel:
    meta = json.loads((artifact_dir / "meta.json").read_text(encoding="utf-8"))
    keras_path = artifact_dir / "regressor.keras"
    keras_regressor = False
    if keras_path.exists():
        from tensorflow import keras

        regressor = keras.models.load_model(keras_path)
        keras_regressor = True
    else:
        regressor = joblib.load(artifact_dir / "regressor.joblib")
    classifier = joblib.load(artifact_dir / "classifier.joblib")
    scaler = joblib.load(artifact_dir / "scaler.joblib")
    temp_model = joblib.load(artifact_dir / "temp_model.joblib")
    return LoadedModel(
        version_id=version_id,
        regressor=regressor,
        classifier=classifier,
        scaler=scaler,
        temp_model=temp_model,
        meta=meta,
        keras_regressor=keras_regressor,
    )


registry = ModelRegistry()
