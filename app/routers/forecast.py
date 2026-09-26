from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import ForecastResponse
from app.security import get_current_user
from app.services.forecast_service import weekly_forecast

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("/weekly", response_model=ForecastResponse)
def get_weekly_forecast(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = weekly_forecast(db, current_user)
    return ForecastResponse(**data)
