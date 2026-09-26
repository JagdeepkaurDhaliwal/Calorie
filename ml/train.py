from __future__ import annotations

import json
import logging
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.preprocessing import StandardScaler

from ml.config import (
    ANN_BATCH,
    ANN_HIDDEN,
    ANN_LR,
    ANN_MAX_EPOCHS,
    ANN_PATIENCE,
    ANN_VAL_FRACTION,
    FEATURE_ORDER,
    KNN_CV,
    KNN_K_GRID,
    RANDOM_STATE,
    RF_N_ESTIMATORS,
)
from ml.evaluate import classification_metrics, regression_metrics
from ml.features import ROOT_DIR
from ml.preprocess import clean_merged, load_merged, load_upload_csv, split_holdout

logger = logging.getLogger(__name__)

try:
    from tensorflow import keras

    HAS_KERAS = True
except Exception:  # pragma: no cover - optional runtime
    HAS_KERAS = False
    keras = None  # type: ignore


@dataclass
class TrainResult:
    artifact_dir: Path
    algorithm: str
    mae: float
    rmse: float
    r2: float
    clf_accuracy: float
    clf_f1: float
    candidates: dict
    meta: dict


def _train_ann(X_train, y_train, X_val, y_val):
    if not HAS_KERAS:
        from sklearn.neural_network import MLPRegressor

        model = MLPRegressor(
            hidden_layer_sizes=ANN_HIDDEN,
            activation="relu",
            solver="adam",
            learning_rate_init=ANN_LR,
            max_iter=400,
            random_state=RANDOM_STATE,
            early_stopping=True,
        )
        model.fit(X_train, y_train)
        return model, "MLPRegressor"

    model = keras.Sequential(
        [
            keras.layers.Input(shape=(X_train.shape[1],)),
            keras.layers.Dense(ANN_HIDDEN[0], activation="relu"),
            keras.layers.Dense(ANN_HIDDEN[1], activation="relu"),
            keras.layers.Dense(1),
        ]
    )
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=ANN_LR), loss="mse")
    callbacks = [
        keras.callbacks.EarlyStopping(
            patience=ANN_PATIENCE, restore_best_weights=True, monitor="val_loss"
        )
    ]
    model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=ANN_MAX_EPOCHS,
        batch_size=ANN_BATCH,
        verbose=0,
        callbacks=callbacks,
    )
    return model, "ANN"


def _predict_regressor(model, name: str, X):
    preds = model.predict(X)
    return np.asarray(preds).reshape(-1)


def _save_regressor(model, name: str, path: Path) -> str:
    if HAS_KERAS and name == "ANN":
        file_path = path / "regressor.keras"
        model.save(file_path)
        return str(file_path)
    file_path = path / "regressor.joblib"
    joblib.dump(model, file_path)
    return str(file_path)


def intensity_labels(calories: pd.Series, duration: pd.Series, t1: float, t2: float) -> pd.Series:
    rate = calories / duration.replace(0, np.nan)
    labels = np.where(rate < t1, "low", np.where(rate < t2, "moderate", "high"))
    return pd.Series(labels, index=calories.index)


def train_bundle(
    extra_csv: Path | None = None,
    dest_dir: Path | None = None,
    skip_ann: bool = False,
) -> TrainResult:
    merged = load_merged()
    train_pool, holdout = split_holdout(clean_merged(merged))
    if extra_csv is not None:
        extra = load_upload_csv(extra_csv)
        train_pool = pd.concat([train_pool, extra], ignore_index=True)

    X_train_df = train_pool[FEATURE_ORDER]
    y_train = train_pool["calories"].values
    X_hold_df = holdout[FEATURE_ORDER]
    y_hold = holdout["calories"].values

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train_df)
    X_hold = scaler.transform(X_hold_df)

    X_ann_train, X_ann_val, y_ann_train, y_ann_val = train_test_split(
        X_train, y_train, test_size=ANN_VAL_FRACTION, random_state=RANDOM_STATE
    )

    candidates: dict[str, dict] = {}
    models: dict[str, object] = {}

    lr = LinearRegression()
    lr.fit(X_train, y_train)
    models["LinearRegression"] = lr
    candidates["LinearRegression"] = regression_metrics(y_hold, _predict_regressor(lr, "LinearRegression", X_hold))

    rf = RandomForestRegressor(n_estimators=RF_N_ESTIMATORS, random_state=RANDOM_STATE, n_jobs=-1)
    rf.fit(X_train, y_train)
    models["RandomForest"] = rf
    candidates["RandomForest"] = regression_metrics(y_hold, _predict_regressor(rf, "RandomForest", X_hold))

    knn_search = GridSearchCV(
        KNeighborsRegressor(),
        {"n_neighbors": KNN_K_GRID},
        cv=KNN_CV,
        scoring="neg_root_mean_squared_error",
        n_jobs=-1,
    )
    knn_search.fit(X_train, y_train)
    knn = knn_search.best_estimator_
    models["KNN"] = knn
    candidates["KNN"] = regression_metrics(y_hold, _predict_regressor(knn, "KNN", X_hold))
    candidates["KNN"]["k"] = int(knn_search.best_params_["n_neighbors"])

    if not skip_ann:
        ann, ann_name = _train_ann(X_ann_train, y_ann_train, X_ann_val, y_ann_val)
        models[ann_name] = ann
        candidates[ann_name] = regression_metrics(y_hold, _predict_regressor(ann, ann_name, X_hold))
    else:
        candidates["ANN"] = {"mae": None, "rmse": None, "r2": None, "skipped": True}

    winner_name = min(
        (name for name, metrics in candidates.items() if metrics.get("rmse") is not None),
        key=lambda name: candidates[name]["rmse"],
    )
    winner = models[winner_name]
    win_metrics = candidates[winner_name]

    kcal_per_min = train_pool["calories"] / train_pool["duration"]
    t1 = float(np.percentile(kcal_per_min, 33))
    t2 = float(np.percentile(kcal_per_min, 66))
    y_clf_train = intensity_labels(train_pool["calories"], train_pool["duration"], t1, t2)
    y_clf_hold = intensity_labels(holdout["calories"], holdout["duration"], t1, t2)

    knn_clf = KNeighborsClassifier(n_neighbors=5)
    knn_clf.fit(X_train, y_clf_train)
    rf_clf = RandomForestClassifier(n_estimators=150, random_state=RANDOM_STATE, n_jobs=-1)
    rf_clf.fit(X_train, y_clf_train)

    knn_clf_m = classification_metrics(y_clf_hold, knn_clf.predict(X_hold))
    rf_clf_m = classification_metrics(y_clf_hold, rf_clf.predict(X_hold))
    if rf_clf_m["f1_macro"] >= knn_clf_m["f1_macro"]:
        classifier, clf_name, clf_metrics = rf_clf, "RandomForestClassifier", rf_clf_m
    else:
        classifier, clf_name, clf_metrics = knn_clf, "KNeighborsClassifier", knn_clf_m

    temp_model = LinearRegression()
    temp_model.fit(train_pool[["duration", "heart_rate"]], train_pool["body_temp"])

    feature_ranges = {
        col: [float(train_pool[col].min()), float(train_pool[col].max())]
        for col in FEATURE_ORDER
        if col != "gender"
    }

    meta = {
        "created_at": datetime.now(UTC).isoformat(),
        "feature_order": FEATURE_ORDER,
        "feature_ranges": feature_ranges,
        "intensity_thresholds": {"t1": round(t1, 4), "t2": round(t2, 4)},
        "regressor": {"algorithm": winner_name, **win_metrics},
        "classifier": {"algorithm": clf_name, **clf_metrics},
        "candidates": candidates,
        "has_keras": HAS_KERAS and winner_name == "ANN",
    }

    if dest_dir is None:
        dest_dir = Path(tempfile.mkdtemp(prefix="caloriecast_bundle_"))
    else:
        dest_dir.mkdir(parents=True, exist_ok=True)

    _save_regressor(winner, winner_name, dest_dir)
    joblib.dump(classifier, dest_dir / "classifier.joblib")
    joblib.dump(scaler, dest_dir / "scaler.joblib")
    joblib.dump(temp_model, dest_dir / "temp_model.joblib")
    (dest_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logger.info("Trained %s RMSE=%s R2=%s", winner_name, win_metrics["rmse"], win_metrics["r2"])

    return TrainResult(
        artifact_dir=dest_dir,
        algorithm=winner_name,
        mae=win_metrics["mae"],
        rmse=win_metrics["rmse"],
        r2=win_metrics["r2"],
        clf_accuracy=clf_metrics["accuracy"],
        clf_f1=clf_metrics["f1_macro"],
        candidates=candidates,
        meta=meta,
    )


def persist_bundle(temp_dir: Path, version_id: int, artifact_root: Path) -> Path:
    target = artifact_root / f"v{version_id}"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(temp_dir, target)
    meta_path = target / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["version"] = version_id
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return target


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = train_bundle()
    print(json.dumps({"algorithm": result.algorithm, "metrics": result.candidates}, indent=2))
