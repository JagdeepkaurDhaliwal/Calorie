from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import PredictRequest, PredictResponse
from app.security import get_current_user
from app.services.prediction_service import predict_and_save

router = APIRouter(prefix="/predict", tags=["predict"])


@router.post("", response_model=PredictResponse)
def predict(
    payload: PredictRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result, workout = predict_and_save(db, current_user, payload, source="manual")
    return PredictResponse(
        workout_id=workout.id,
        predicted_calories=result.kcal,
        intensity=result.intensity,
        model_version=result.version_id,
        extrapolated=result.extrapolated,
        warnings=result.warnings,
    )
