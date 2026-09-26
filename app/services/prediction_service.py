from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.errors import BadRequest, ValidationError
from app.models import User, Workout
from app.services.workout_service import save_workout
from ml.features import build_features
from ml.registry import registry


@dataclass
class PredictionResult:
    kcal: float
    intensity: str
    version_id: int
    extrapolated: bool
    warnings: list[str]


def resolve_inputs(user: User, payload) -> dict:
    gender = payload.gender or user.gender
    age = payload.age if payload.age is not None else user.age
    height = payload.height if payload.height is not None else user.height_cm
    weight = payload.weight if payload.weight is not None else user.weight_kg

    # Flexible height conversion (ft/in to cm)
    if getattr(payload, "height_unit", "cm") == "ft" or getattr(payload, "height_feet", None) is not None:
        ft = float(payload.height_feet or 0.0)
        inch = float(payload.height_inches or 0.0)
        height = round((ft * 30.48) + (inch * 2.54), 1)

    # Flexible weight conversion (lbs to kg)
    if getattr(payload, "weight_unit", "kg") == "lbs" and payload.weight is not None:
        weight = round(float(payload.weight) * 0.45359237, 1)

    missing = [
        name
        for name, value in (
            ("gender", gender),
            ("age", age),
            ("height", height),
            ("weight", weight),
        )
        if value is None
    ]
    if missing:
        raise ValidationError(
            "Profile fields are required for prediction",
            details=[{"field": f, "issue": "missing from request and profile"} for f in missing],
        )

    # Flexible duration (hours + minutes)
    duration = payload.duration
    if duration is None and (getattr(payload, "duration_hours", None) is not None or getattr(payload, "duration_minutes", None) is not None):
        duration = (float(payload.duration_hours or 0.0) * 60.0) + float(payload.duration_minutes or 0.0)
    if duration is None:
        duration = 25.0

    # Flexible body temp (°F to °C)
    body_temp = payload.body_temp
    if getattr(payload, "body_temp_unit", "C") == "F" and body_temp is not None:
        body_temp = round((float(body_temp) - 32.0) * (5.0 / 9.0), 1)
    if body_temp is None:
        body_temp = 38.0

    # Flexible heart rate
    heart_rate = payload.heart_rate
    if heart_rate is None:
        intensity_val = str(getattr(payload, "intensity", "moderate") or "moderate").lower()
        heart_rate = {"low": 110.0, "moderate": 135.0, "high": 160.0}.get(intensity_val, 130.0)

    return {
        "gender": gender,
        "age": age,
        "height": height,
        "weight": weight,
        "duration": duration,
        "heart_rate": heart_rate,
        "body_temp": body_temp,
    }



def predict_from_inputs(inputs: dict) -> PredictionResult:
    model = registry.active()
    x = build_features(
        gender=inputs["gender"],
        age=inputs["age"],
        height=inputs["height"],
        weight=inputs["weight"],
        duration=inputs["duration"],
        heart_rate=inputs["heart_rate"],
        body_temp=inputs["body_temp"],
        meta=model.meta,
    )
    kcal = max(float(model.regressor_predict(x)[0]), 0.0)
    intensity = str(model.classify(x)[0])
    warnings = model.range_warnings_for(inputs)
    return PredictionResult(
        kcal=round(kcal, 2),
        intensity=intensity,
        version_id=model.version_id,
        extrapolated=bool(warnings),
        warnings=warnings,
    )


def predict_and_save(db: Session, user: User, payload, source: str = "manual") -> tuple[PredictionResult, Workout]:
    inputs = resolve_inputs(user, payload)
    result = predict_from_inputs(inputs)
    workout = save_workout(
        db,
        user_id=user.id,
        duration_min=inputs["duration"],
        heart_rate=inputs["heart_rate"],
        body_temp=inputs["body_temp"],
        predicted_calories=result.kcal,
        intensity=result.intensity,
        model_version_id=result.version_id,
        source=source,
        extrapolated=result.extrapolated,
    )
    return result, workout
