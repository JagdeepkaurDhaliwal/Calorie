from datetime import UTC, datetime, date
import logging
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import FoodItem, Meal, MealItem, User, WorkoutExercise
from app.schemas import (
    DailyNutritionSummary,
    MealCreate,
    MealOut,
    MealItemCreate,
)

logger = logging.getLogger(__name__)

DEFAULT_FOODS = [
    # Grains & Staple Breads
    {"name": "White Rice (Cooked)", "category": "grains", "serving_size": "1 cup (158g)", "calories": 205.0, "protein": 4.2, "carbs": 44.5, "fat": 0.4},
    {"name": "Brown Rice (Cooked)", "category": "grains", "serving_size": "1 cup (195g)", "calories": 218.0, "protein": 4.5, "carbs": 45.8, "fat": 1.6},
    {"name": "Whole Wheat Roti / Chapati", "category": "grains", "serving_size": "1 medium (40g)", "calories": 110.0, "protein": 3.5, "carbs": 22.0, "fat": 0.9},
    {"name": "Whole Wheat Bread", "category": "grains", "serving_size": "2 slices (60g)", "calories": 160.0, "protein": 6.0, "carbs": 28.0, "fat": 2.0},
    {"name": "Rolled Oatmeal (Cooked)", "category": "grains", "serving_size": "1 bowl (234g)", "calories": 158.0, "protein": 5.9, "carbs": 27.0, "fat": 3.2},
    {"name": "Cooked Quinoa", "category": "grains", "serving_size": "1 cup (185g)", "calories": 222.0, "protein": 8.1, "carbs": 39.4, "fat": 3.6},

    # Proteins & Lentils
    {"name": "Yellow Moong / Toor Dal (Cooked)", "category": "protein", "serving_size": "1 bowl (200g)", "calories": 180.0, "protein": 9.5, "carbs": 28.0, "fat": 2.8},
    {"name": "Paneer (Cottage Cheese)", "category": "dairy", "serving_size": "100g", "calories": 265.0, "protein": 18.3, "carbs": 3.4, "fat": 20.8},
    {"name": "Whole Boiled Egg", "category": "protein", "serving_size": "1 large (50g)", "calories": 78.0, "protein": 6.3, "carbs": 0.6, "fat": 5.3},
    {"name": "Egg Whites (Cooked)", "category": "protein", "serving_size": "3 large (99g)", "calories": 51.0, "protein": 10.8, "carbs": 0.7, "fat": 0.2},
    {"name": "Grilled Chicken Breast", "category": "protein", "serving_size": "100g", "calories": 165.0, "protein": 31.0, "carbs": 0.0, "fat": 3.6},
    {"name": "Salmon Fillet (Baked)", "category": "protein", "serving_size": "100g", "calories": 208.0, "protein": 22.0, "carbs": 0.0, "fat": 13.0},
    {"name": "Tofu (Firm)", "category": "protein", "serving_size": "100g", "calories": 144.0, "protein": 15.5, "carbs": 2.8, "fat": 8.0},
    {"name": "Whey Protein Shake (with Water)", "category": "protein", "serving_size": "1 scoop (30g)", "calories": 120.0, "protein": 24.0, "carbs": 2.0, "fat": 1.5},

    # Dairy
    {"name": "Greek Yogurt (Plain, Low Fat)", "category": "dairy", "serving_size": "1 cup (200g)", "calories": 140.0, "protein": 20.0, "carbs": 7.0, "fat": 3.0},
    {"name": "Whole Cow Milk", "category": "dairy", "serving_size": "1 glass (240ml)", "calories": 150.0, "protein": 8.0, "carbs": 12.0, "fat": 8.0},

    # Fruits & Vegetables
    {"name": "Banana", "category": "fruits", "serving_size": "1 medium (118g)", "calories": 105.0, "protein": 1.3, "carbs": 27.0, "fat": 0.3},
    {"name": "Apple", "category": "fruits", "serving_size": "1 medium (182g)", "calories": 95.0, "protein": 0.5, "carbs": 25.0, "fat": 0.3},
    {"name": "Mixed Green Garden Salad", "category": "vegetables", "serving_size": "1 large bowl (150g)", "calories": 45.0, "protein": 2.2, "carbs": 8.5, "fat": 0.5},
    {"name": "Steamed Broccoli", "category": "vegetables", "serving_size": "1 cup (91g)", "calories": 35.0, "protein": 2.6, "carbs": 7.0, "fat": 0.4},
    {"name": "Mixed Vegetable Curry", "category": "vegetables", "serving_size": "1 bowl (200g)", "calories": 140.0, "protein": 4.0, "carbs": 16.0, "fat": 7.0},

    # Healthy Fats & Snacks
    {"name": "Mixed Almonds and Walnuts", "category": "snacks", "serving_size": "Handful (30g)", "calories": 185.0, "protein": 5.5, "carbs": 5.0, "fat": 16.5},
    {"name": "Natural Peanut Butter", "category": "snacks", "serving_size": "2 tbsp (32g)", "calories": 190.0, "protein": 8.0, "carbs": 6.0, "fat": 16.0},
    {"name": "Roasted Chana (Chickpeas)", "category": "snacks", "serving_size": "1 bowl (50g)", "calories": 180.0, "protein": 9.0, "carbs": 29.0, "fat": 3.0},
]


def init_default_foods(db: Session) -> int:
    count = db.query(FoodItem).count()
    if count > 0:
        return count
    for f in DEFAULT_FOODS:
        item = FoodItem(
            name=f["name"],
            category=f["category"],
            serving_size=f["serving_size"],
            calories=f["calories"],
            protein=f["protein"],
            carbs=f["carbs"],
            fat=f["fat"],
        )
        db.add(item)
    db.commit()
    logger.info("Seeded %d default food items.", len(DEFAULT_FOODS))
    return len(DEFAULT_FOODS)


def get_food_catalogue(db: Session, category: str | None = None, search: str | None = None) -> list[FoodItem]:
    init_default_foods(db)
    query = db.query(FoodItem)
    if category:
        query = query.filter(FoodItem.category == category.lower())
    if search:
        query = query.filter(FoodItem.name.ilike(f"%{search.strip()}%"))
    return query.order_by(FoodItem.category, FoodItem.name).all()


def log_meal(db: Session, user: User, payload: MealCreate) -> Meal:
    init_default_foods(db)
    meal_date = payload.date or datetime.now(UTC).strftime("%Y-%m-%d")
    meal_type = payload.meal_type.lower()

    # Find or create meal for this user, date, and meal_type
    meal = (
        db.query(Meal)
        .filter(Meal.user_id == user.id, Meal.date == meal_date, Meal.meal_type == meal_type)
        .first()
    )

    if not meal:
        meal = Meal(
            user_id=user.id,
            meal_type=meal_type,
            date=meal_date,
            total_calories=0.0,
            total_protein=0.0,
            total_carbs=0.0,
            total_fat=0.0,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(meal)
        db.commit()
        db.refresh(meal)

    # Add items
    for item_in in payload.items:
        item = MealItem(
            meal_id=meal.id,
            food_name=item_in.food_name,
            quantity=item_in.quantity,
            calories=round(float(item_in.calories), 1),
            protein=round(float(item_in.protein), 1),
            carbs=round(float(item_in.carbs), 1),
            fat=round(float(item_in.fat), 1),
            is_ai_detected=False,
        )
        db.add(item)

    db.commit()
    _recalc_meal_totals(db, meal.id)
    db.refresh(meal)
    return meal


def _recalc_meal_totals(db: Session, meal_id: int):
    items = db.query(MealItem).filter(MealItem.meal_id == meal_id).all()
    cals = sum(i.calories for i in items)
    protein = sum(i.protein for i in items)
    carbs = sum(i.carbs for i in items)
    fat = sum(i.fat for i in items)

    meal = db.get(Meal, meal_id)
    if meal:
        meal.total_calories = round(cals, 1)
        meal.total_protein = round(protein, 1)
        meal.total_carbs = round(carbs, 1)
        meal.total_fat = round(fat, 1)
        db.commit()


def get_daily_nutrition(db: Session, user: User, target_date: str | None = None) -> DailyNutritionSummary:
    init_default_foods(db)
    if not target_date:
        target_date = datetime.now(UTC).strftime("%Y-%m-%d")

    target = float(user.daily_calorie_target or 2000.0)

    # Retrieve all meals for this date
    meals_query = (
        db.query(Meal)
        .filter(Meal.user_id == user.id, Meal.date == target_date)
        .all()
    )

    meals_by_type: dict[str, Meal | None] = {
        "breakfast": None,
        "lunch": None,
        "dinner": None,
        "snack": None,
    }

    consumed_calories = 0.0
    total_protein = 0.0
    total_carbs = 0.0
    total_fat = 0.0

    for m in meals_query:
        meals_by_type[m.meal_type] = m
        consumed_calories += m.total_calories
        total_protein += m.total_protein
        total_carbs += m.total_carbs
        total_fat += m.total_fat

    # Calculate exercise calories for this date
    exercise_kcal = (
        db.query(func.coalesce(func.sum(WorkoutExercise.calories_burned), 0.0))
        .filter(
            WorkoutExercise.user_id == user.id,
            func.date(WorkoutExercise.created_at) == target_date,
        )
        .scalar()
    ) or 0.0

    consumed_calories = round(consumed_calories, 1)
    exercise_kcal = round(float(exercise_kcal), 1)
    remaining_calories = round(target - consumed_calories, 1)
    net_calories = round(consumed_calories - exercise_kcal, 1)

    # Determine status
    if consumed_calories > target + 50.0:
        status = "over_target"
        status_message = "⚠ Calories are above today's target."
    elif consumed_calories >= target - 150.0:
        status = "approaching_target"
        status_message = "You are approaching your daily calorie target."
    elif consumed_calories >= target - 350.0:
        status = "within_target"
        status_message = "Great balance! You are within your daily target range."
    else:
        status = "below_target"
        status_message = f"You have {remaining_calories:.0f} kcal remaining today."

    meals_out = {
        k: (MealOut.model_validate(v) if v else None)
        for k, v in meals_by_type.items()
    }

    return DailyNutritionSummary(
        date=target_date,
        daily_target=target,
        consumed_calories=consumed_calories,
        remaining_calories=remaining_calories,
        exercise_calories=exercise_kcal,
        net_calories=net_calories,
        status=status,
        status_message=status_message,
        total_protein=round(total_protein, 1),
        total_carbs=round(total_carbs, 1),
        total_fat=round(total_fat, 1),
        meals=meals_out,
    )
