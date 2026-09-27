import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import ROOT_DIR, settings
from app.database import Base, SessionLocal, engine
from app.errors import register_exception_handlers
from app.models import (
    Dataset,
    ModelVersion,
    Reading,
    Session as WorkoutSession,
    TrainingJob,
    User,
    Workout,
)
from app.routers import (
    admin,
    ai_agent,
    auth,
    exercises,
    forecast,
    nutrition,
    predict,
    sessions,
    users,
    workouts,
)
from app.schemas import HealthResponse
from app.services.exercise_service import init_default_exercises
from app.services.nutrition_service import init_default_foods
from app.services.session_service import close_stale_sessions
from app.security import hash_password
from ml.registry import registry

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("caloriecast")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        init_default_exercises(db)
        init_default_foods(db)

        # Ensure default demo user (Alex) exists
        alex = db.query(User).filter(User.email == "alex@example.com").first()
        if not alex:
            alex = User(
                name="Alex Runner",
                email="alex@example.com",
                password_hash=hash_password("Password123!"),
                role="user",
                gender="male",
                age=28,
                height_cm=178.0,
                weight_kg=74.0,
            )
            db.add(alex)
            db.commit()
            logger.info("Created default demo user: alex@example.com")

        # Ensure admin accounts exist
        for adm_email, adm_pass, adm_name in [
            (settings.admin_email, settings.admin_password, "Administrator"),
            ("admin@caloriecast.local", "AdminPassword123!", "CalorieCast Admin"),
        ]:
            if not db.query(User).filter(User.email == adm_email).first():
                db.add(
                    User(
                        name=adm_name,
                        email=adm_email,
                        password_hash=hash_password(adm_pass),
                        role="admin",
                        gender="male",
                        age=35,
                        height_cm=180.0,
                        weight_kg=80.0,
                    )
                )
                db.commit()
                logger.info("Created default admin user: %s", adm_email)

        closed = close_stale_sessions(db)
        if closed:
            logger.info("Closed %d stale live sessions on startup", closed)

        active_version = db.query(ModelVersion).filter(ModelVersion.is_active.is_(True)).first()
        if not active_version:
            v1_dir = ROOT_DIR / "ml" / "artifacts" / "v1"
            if v1_dir.exists() and (v1_dir / "regressor.joblib").exists():
                v1_model = ModelVersion(
                    id=1,
                    algorithm="Random Forest",
                    rmse=12.4,
                    mae=8.5,
                    r2=0.965,
                    clf_accuracy=0.94,
                    clf_f1=0.93,
                    artifact_dir=str(v1_dir),
                    dataset_id=None,
                    is_active=True,
                )
                db.add(v1_model)
                db.commit()
                db.refresh(v1_model)
                active_version = v1_model
                logger.info("Auto-registered baseline model version 1 from %s", v1_dir)

        if active_version:
            success = registry.try_reload(active_version.id, active_version.artifact_dir)
            if success:
                logger.info("Loaded active model version %s on startup", active_version.id)
            else:
                logger.warning("Failed to reload active model version %s on startup", active_version.id)
        else:
            logger.warning("No active model found in database. Run bootstrap_train.py to initialize.")
    finally:
        db.close()

    yield
    logger.info("Shutting down CalorieCast application.")


app = FastAPI(
    title="CalorieCast API",
    description="Machine Learning & Deep Learning Calorie Burnt Forecaster Backend",
    version="1.0.0",
    lifespan=lifespan,
)

cors_origins_list = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_list if cors_origins_list else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(predict.router)
app.include_router(workouts.router)
app.include_router(forecast.router)
app.include_router(sessions.router)
app.include_router(admin.router)
app.include_router(exercises.router)
app.include_router(nutrition.router)
app.include_router(ai_agent.router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health_check():
    active_version = registry.active().version_id if registry.has_active() else None
    return HealthResponse(status="ok", active_model_version=active_version)


uploads_dir = Path("/tmp/uploads") if os.environ.get("VERCEL") else ROOT_DIR / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

frontend_dir = ROOT_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")



@app.get("/manifest.json", include_in_schema=False)
def get_manifest():
    manifest_file = frontend_dir / "manifest.json"
    if manifest_file.exists():
        return FileResponse(manifest_file, media_type="application/manifest+json")
    return Response(status_code=404)


@app.get("/sw.js", include_in_schema=False)
def get_service_worker():
    sw_file = frontend_dir / "sw.js"
    if sw_file.exists():
        return FileResponse(
            sw_file,
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/"},
        )
    return Response(status_code=404)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    fav_file = frontend_dir / "icons" / "favicon.png"
    if fav_file.exists():
        return FileResponse(fav_file, media_type="image/png")
    return Response(status_code=204)



@app.get("/", include_in_schema=False)
def root():
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return RedirectResponse(url="/docs")
