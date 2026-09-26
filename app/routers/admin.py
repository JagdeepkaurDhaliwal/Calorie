from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import RetrainRequest
from app.security import require_admin
from app.services.admin_service import (
    activate_version,
    get_job,
    list_models,
    queue_retrain,
    run_retrain_job,
    save_upload,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/upload-data", status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    content = await file.read()
    dataset = save_upload(db, admin_id=admin.id, filename=file.filename or "upload.csv", content=content)
    return {
        "dataset_id": dataset.id,
        "rows": dataset.row_count,
        "status": dataset.status,
        "message": dataset.message,
    }


@router.post("/retrain", status_code=status.HTTP_202_ACCEPTED)
def start_retrain(
    payload: RetrainRequest,
    background_tasks: BackgroundTasks,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    job = queue_retrain(db, payload.dataset_id)
    background_tasks.add_task(run_retrain_job, job.id)
    return {"job_id": job.id}


@router.get("/retrain/{job_id}")
def check_retrain_job(
    job_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    job = get_job(db, job_id)
    return {
        "id": job.id,
        "dataset_id": job.dataset_id,
        "status": job.status,
        "message": job.message,
        "activated": job.activated,
        "model_version_id": job.model_version_id,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


@router.get("/models")
def get_all_models(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return list_models(db)


@router.post("/models/{model_id}/activate")
def activate_model(
    model_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    version = activate_version(db, model_id)
    return {
        "id": version.id,
        "algorithm": version.algorithm,
        "is_active": version.is_active,
        "message": f"Successfully activated model v{version.id}",
    }
