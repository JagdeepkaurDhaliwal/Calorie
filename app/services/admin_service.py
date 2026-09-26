from __future__ import annotations

import json
import logging
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.config import ROOT_DIR, settings
from app.database import SessionLocal
from app.errors import BadRequest, Conflict, NotFound
from app.models import Dataset, ModelVersion, TrainingJob
from ml.config import RANGES
from ml.registry import registry
from ml.train import persist_bundle, train_bundle

logger = logging.getLogger(__name__)

UPLOAD_DIR = ROOT_DIR / "data" / "uploads"
REQUIRED_COLUMNS = {
    "Gender",
    "Age",
    "Height",
    "Weight",
    "Duration",
    "Heart_Rate",
    "Body_Temp",
    "Calories",
}
ALIASES = {
    "gender": "Gender",
    "age": "Age",
    "height": "Height",
    "weight": "Weight",
    "duration": "Duration",
    "heart_rate": "Heart_Rate",
    "body_temp": "Body_Temp",
    "calories": "Calories",
}


def try_activate(db: Session, new_version: ModelVersion, force: bool = False) -> bool:
    active = db.query(ModelVersion).filter_by(is_active=True).first()
    better = force or active is None or new_version.rmse < active.rmse
    if not better:
        return False
    if active:
        active.is_active = False
        db.flush()
    new_version.is_active = True
    db.commit()
    ok = registry.try_reload(new_version.id, new_version.artifact_dir)
    if not ok:
        new_version.is_active = False
        if active:
            active.is_active = True
        db.commit()
        return False
    return True


def save_upload(db: Session, admin_id: int, filename: str, content: bytes) -> Dataset:
    if not filename.lower().endswith(".csv"):
        raise BadRequest("Only CSV files are accepted")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise BadRequest(f"File exceeds {settings.max_upload_mb} MB")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored = UPLOAD_DIR / f"{uuid.uuid4().hex}.csv"
    stored.write_bytes(content)
    status, message, row_count = _validate_csv(stored)
    dataset = Dataset(
        original_name=Path(filename).name,
        stored_path=str(stored),
        row_count=row_count,
        status=status,
        message=message,
        uploaded_by=admin_id,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    if status == "rejected":
        raise BadRequest(message)
    return dataset


def _validate_csv(path: Path) -> tuple[str, str, int]:
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        return "rejected", f"Could not parse CSV: {exc}", 0
    for src, dest in ALIASES.items():
        if src in df.columns and dest not in df.columns:
            df = df.rename(columns={src: dest})
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        return "rejected", f"Missing columns: {sorted(missing)}", 0
    numeric = ["Age", "Height", "Weight", "Duration", "Heart_Rate", "Body_Temp", "Calories"]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    missing_frac = df[numeric].isna().any(axis=1).mean()
    if missing_frac > 0.05:
        return "rejected", f"Too many missing values ({missing_frac:.0%}; max 5%)", len(df)
    gender_ok = df["Gender"].astype(str).str.lower().isin(["male", "female", "m", "f", "0", "1"])
    if not gender_ok.all():
        return "rejected", "Gender must be male or female", len(df)
    range_map = {
        "Age": "age",
        "Height": "height",
        "Weight": "weight",
        "Duration": "duration",
        "Heart_Rate": "heart_rate",
        "Body_Temp": "body_temp",
    }
    for col, key in range_map.items():
        lo, hi = RANGES[key]
        series = df[col].dropna()
        if ((series < lo) | (series > hi)).any():
            return "rejected", f"{col} has values outside {lo}-{hi}", len(df)
    return "valid", "ok", int(len(df))


def queue_retrain(db: Session, dataset_id: int | None) -> TrainingJob:
    running = (
        db.query(TrainingJob)
        .filter(TrainingJob.status.in_(("queued", "running")))
        .first()
    )
    if running:
        raise Conflict("A retraining job is already running")
    if dataset_id is not None:
        dataset = db.get(Dataset, dataset_id)
        if not dataset or dataset.status != "valid":
            raise BadRequest("dataset_id must refer to a valid uploaded dataset")
    job = TrainingJob(dataset_id=dataset_id, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def run_retrain_job(job_id: int) -> None:
    db = SessionLocal()
    extra_csv = None
    temp_dir = None
    try:
        job = db.get(TrainingJob, job_id)
        if not job:
            return
        job.status = "running"
        job.started_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()
        if job.dataset_id:
            dataset = db.get(Dataset, job.dataset_id)
            extra_csv = Path(dataset.stored_path) if dataset else None
        result = train_bundle(extra_csv=extra_csv)
        temp_dir = result.artifact_dir
        version = ModelVersion(
            algorithm=result.algorithm,
            artifact_dir="pending",
            mae=result.mae,
            rmse=result.rmse,
            r2=result.r2,
            clf_accuracy=result.clf_accuracy,
            clf_f1=result.clf_f1,
            candidates_json=json.dumps(result.candidates),
            training_job_id=job.id,
            is_active=False,
        )
        db.add(version)
        db.flush()
        target = persist_bundle(result.artifact_dir, version.id, settings.artifact_path)
        version.artifact_dir = str(target)
        db.commit()
        db.refresh(version)
        activated = try_activate(db, version, force=False)
        job.model_version_id = version.id
        job.activated = activated
        job.status = "succeeded"
        if activated:
            job.message = f"Activated {version.algorithm} v{version.id} (RMSE {version.rmse})"
        else:
            job.message = "candidate not better; not activated"
        job.finished_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()
    except Exception as exc:
        logger.exception("Retrain job %s failed", job_id)
        job = db.get(TrainingJob, job_id)
        if job:
            job.status = "failed"
            job.message = str(exc)
            job.finished_at = datetime.now(UTC).replace(tzinfo=None)
            db.commit()
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
    finally:
        db.close()


def list_models(db: Session) -> list[dict]:
    rows = db.query(ModelVersion).order_by(ModelVersion.id.desc()).all()
    out = []
    for row in rows:
        out.append(
            {
                "id": row.id,
                "algorithm": row.algorithm,
                "mae": row.mae,
                "rmse": row.rmse,
                "r2": row.r2,
                "clf_accuracy": row.clf_accuracy,
                "clf_f1": row.clf_f1,
                "is_active": row.is_active,
                "candidates": row.candidates(),
                "created_at": row.created_at,
            }
        )
    return out


def activate_version(db: Session, version_id: int) -> ModelVersion:
    version = db.get(ModelVersion, version_id)
    if not version:
        raise NotFound("Model version not found")
    ok = try_activate(db, version, force=True)
    if not ok:
        raise BadRequest("Failed to load the selected model bundle")
    db.refresh(version)
    return version


def get_job(db: Session, job_id: int) -> TrainingJob:
    job = db.get(TrainingJob, job_id)
    if not job:
        raise NotFound("Training job not found")
    return job
