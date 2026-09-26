import logging
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.database import Base, SessionLocal, engine
from app.models import ModelVersion, User, Workout
from app.security import hash_password
from app.services.prediction_service import predict_from_inputs
from ml.registry import registry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_demo")

DEMO_USERS = [
    {
        "name": "Alex Runner",
        "email": "alex@example.com",
        "password": "Password123!",
        "gender": "male",
        "age": 28,
        "height_cm": 178.0,
        "weight_kg": 74.0,
        "days": [0, 2, 4],  # Mon, Wed, Fri
    },
    {
        "name": "Sarah Cardio",
        "email": "sarah@example.com",
        "password": "Password123!",
        "gender": "female",
        "age": 34,
        "height_cm": 165.0,
        "weight_kg": 58.0,
        "days": [1, 3, 5],  # Tue, Thu, Sat
    },
    {
        "name": "David Lift",
        "email": "david@example.com",
        "password": "Password123!",
        "gender": "male",
        "age": 42,
        "height_cm": 182.0,
        "weight_kg": 85.0,
        "days": [0, 1, 3, 5],
    },
    {
        "name": "Elena Fit",
        "email": "elena@example.com",
        "password": "Password123!",
        "gender": "female",
        "age": 25,
        "height_cm": 170.0,
        "weight_kg": 62.0,
        "days": [0, 2, 4, 6],
    },
    {
        "name": "Michael Pace",
        "email": "michael@example.com",
        "password": "Password123!",
        "gender": "male",
        "age": 50,
        "height_cm": 175.0,
        "weight_kg": 80.0,
        "days": [2, 4, 6],
    },
]


def ensure_active_model(db):
    if not registry.has_active():
        active_version = db.query(ModelVersion).filter(ModelVersion.is_active.is_(True)).first()
        if active_version:
            registry.reload(active_version.id, active_version.artifact_dir)
        else:
            raise RuntimeError("No active model available. Run bootstrap_train.py first!")


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    random.seed(42)

    try:
        ensure_active_model(db)
        active_model = registry.active()
        now = datetime.now(UTC)

        for udata in DEMO_USERS:
            email = udata["email"]
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    name=udata["name"],
                    email=email,
                    password_hash=hash_password(udata["password"]),
                    role="user",
                    gender=udata["gender"],
                    age=udata["age"],
                    height_cm=udata["height_cm"],
                    weight_kg=udata["weight_kg"],
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                logger.info("Created demo user %s (%s)", user.name, user.email)
            else:
                logger.info("User %s already exists. Seeding new workouts if needed.", user.email)

            # Clear existing seed workouts for clean re-seeding
            db.query(Workout).filter(Workout.user_id == user.id, Workout.source == "seed").delete()
            db.commit()

            # Generate 8 weeks of workouts
            workout_count = 0
            for week_offset in range(8, 0, -1):
                week_start = now - timedelta(weeks=week_offset)
                for day_idx in udata["days"]:
                    workout_date = week_start + timedelta(days=day_idx, hours=random.randint(6, 19), minutes=random.randint(0, 59))
                    if workout_date >= now:
                        continue

                    duration = round(random.uniform(15.0, 45.0), 1)
                    heart_rate = round(random.uniform(105.0, 155.0), 1)
                    body_temp = active_model.estimate_body_temp(duration, heart_rate)

                    pred = predict_from_inputs(
                        {
                            "gender": user.gender,
                            "age": user.age,
                            "height": user.height_cm,
                            "weight": user.weight_kg,
                            "duration": duration,
                            "heart_rate": heart_rate,
                            "body_temp": body_temp,
                        }
                    )

                    workout = Workout(
                        user_id=user.id,
                        duration_min=duration,
                        heart_rate=heart_rate,
                        body_temp=round(body_temp, 2),
                        predicted_calories=pred.kcal,
                        intensity=pred.intensity,
                        model_version_id=active_model.version_id,
                        source="seed",
                        extrapolated=pred.extrapolated,
                        created_at=workout_date.replace(tzinfo=None),
                    )
                    db.add(workout)
                    workout_count += 1

            db.commit()
            logger.info("Seeded %d workouts for user %s (%s)", workout_count, user.name, user.email)

        logger.info("Demo data seeding completed successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
