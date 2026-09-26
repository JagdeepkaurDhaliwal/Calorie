import json
import logging
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import ModelVersion
from app.services.admin_service import try_activate
from ml.registry import registry
from ml.train import persist_bundle, train_bundle

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bootstrap")


def main():
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)

    logger.info("Training initial model bundle (LinearRegression, RandomForest, KNN, ANN/MLP)...")
    result = train_bundle()

    logger.info("Winner: %s with RMSE: %.4f (MAE: %.4f, R²: %.4f)", result.algorithm, result.rmse, result.mae, result.r2)
    logger.info("Classifier Accuracy: %.4f, F1 Macro: %.4f", result.clf_accuracy, result.clf_f1)
    logger.info("Candidates evaluated: %s", list(result.candidates.keys()))

    db = SessionLocal()
    try:
        version = ModelVersion(
            algorithm=result.algorithm,
            artifact_dir="pending",
            mae=result.mae,
            rmse=result.rmse,
            r2=result.r2,
            clf_accuracy=result.clf_accuracy,
            clf_f1=result.clf_f1,
            candidates_json=json.dumps(result.candidates),
            training_job_id=None,
            is_active=False,
        )
        db.add(version)
        db.flush()

        logger.info("Persisting model bundle to artifact directory...")
        target_dir = persist_bundle(result.artifact_dir, version.id, settings.artifact_path)
        version.artifact_dir = str(target_dir)
        db.commit()
        db.refresh(version)

        logger.info("Activating model version v%s...", version.id)
        activated = try_activate(db, version, force=True)
        if not activated:
            logger.error("Failed to activate model v%s in registry!", version.id)
            sys.exit(1)

        logger.info("Successfully activated model v%s! Current active in registry: %s", version.id, registry.active().version_id)
    finally:
        db.close()


if __name__ == "__main__":
    main()
