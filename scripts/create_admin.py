import argparse
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import User
from app.security import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("create_admin")


def main():
    parser = argparse.ArgumentParser(description="Create or promote an administrator account.")
    parser.add_argument("--email", default=settings.admin_email, help="Admin email address")
    parser.add_argument("--password", default=settings.admin_password, help="Admin password")
    parser.add_argument("--name", default="Administrator", help="Admin display name")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == args.email.lower().strip()).first()
        if user:
            logger.info("User '%s' exists. Updating role to admin and resetting password...", user.email)
            user.role = "admin"
            user.password_hash = hash_password(args.password)
            user.name = args.name
            db.commit()
            logger.info("Admin account '%s' updated successfully.", user.email)
        else:
            logger.info("Creating new admin user '%s'...", args.email)
            admin_user = User(
                name=args.name,
                email=args.email.lower().strip(),
                password_hash=hash_password(args.password),
                role="admin",
                age=32,
                gender="male",
                height_cm=175.0,
                weight_kg=72.0,
            )
            db.add(admin_user)
            db.commit()
            logger.info("Admin user '%s' created successfully (ID: %s).", admin_user.email, admin_user.id)
    finally:
        db.close()


if __name__ == "__main__":
    main()
