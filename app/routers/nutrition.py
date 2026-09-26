from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import (
    DailyNutritionSummary,
    FoodItemOut,
    FoodRecommendationOut,
    MealCreate,
    MealOut,
)
from app.security import get_current_user
from app.services.ai_agent_service import get_food_recommendations
from app.services.nutrition_service import (
    get_daily_nutrition,
    get_food_catalogue,
    log_meal,
)

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.get("/today", response_model=DailyNutritionSummary)
def get_today_nutrition(
    date: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_daily_nutrition(db, current_user, target_date=date)


@router.post("/meals", response_model=MealOut, status_code=status.HTTP_201_CREATED)
def create_meal(
    payload: MealCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    meal = log_meal(db, current_user, payload)
    return MealOut.model_validate(meal)


@router.get("/food-items", response_model=list[FoodItemOut])
def list_food_items(
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = get_food_catalogue(db, category=category, search=search)
    return [FoodItemOut.model_validate(i) for i in items]


@router.get("/recommendations", response_model=list[FoodRecommendationOut])
def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_food_recommendations(db, current_user)
