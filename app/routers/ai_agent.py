import json
import os
import uuid
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AIPlan, User
from app.schemas import (
    AIChatRequest,
    AIChatResponse,
    AIPlanResponse,
    FoodAnalysisResponse,
    FoodConfirmRequest,
    MealOut,
    PersonalizedPlanRequest,
)
from app.security import get_current_user
from app.services.ai_agent_service import (
    analyze_food_image,
    chat_with_agent,
    confirm_food_analysis,
    generate_general_plan,
    generate_personalized_plan,
)

router = APIRouter(tags=["ai_agent"])

UPLOAD_DIR = "/tmp/uploads" if os.environ.get("VERCEL") else "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/food/analyze-image", response_model=FoodAnalysisResponse)
async def upload_and_analyze_food(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contents = await file.read()
    orig_ext = os.path.splitext(file.filename or "food.jpg")[1] or ".jpg"
    safe_name = f"{uuid.uuid4().hex[:12]}_{file.filename or 'food.jpg'}"
    dest_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(dest_path, "wb") as f:
        f.write(contents)

    analysis_res = analyze_food_image(
        file_bytes=contents,
        filename=file.filename or safe_name,
        user_id=current_user.id,
        db=db,
    )
    return analysis_res


@router.post("/food/confirm", response_model=MealOut, status_code=status.HTTP_201_CREATED)
def confirm_analyzed_food(
    payload: FoodConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    meal = confirm_food_analysis(db, current_user, payload)
    return MealOut.model_validate(meal)


@router.post("/ai/general-plan", response_model=AIPlanResponse)
def create_general_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return generate_general_plan(db, current_user)


@router.post("/ai/personalized-plan", response_model=AIPlanResponse)
def create_personalized_plan(
    payload: PersonalizedPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return generate_personalized_plan(db, current_user, payload)


@router.get("/ai/current-plan", response_model=AIPlanResponse | None)
def get_current_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = (
        db.query(AIPlan)
        .filter(AIPlan.user_id == current_user.id, AIPlan.is_active == True)
        .order_by(AIPlan.created_at.desc())
        .first()
    )
    if not plan:
        return None
    return AIPlanResponse(
        id=plan.id,
        plan_type=plan.plan_type,
        goal=plan.goal,
        title=plan.title,
        summary=plan.summary,
        workout_plan=json.loads(plan.workout_plan_json),
        nutrition_plan=json.loads(plan.nutrition_plan_json),
        daily_calorie_target=plan.daily_calorie_target,
        created_at=plan.created_at,
    )


@router.post("/ai/assistant-chat", response_model=AIChatResponse)
def assistant_chat(
    payload: AIChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return chat_with_agent(db, current_user, payload.message)
