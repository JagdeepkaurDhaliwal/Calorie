from sqlalchemy.orm import Session

from app.errors import Conflict, Unauthorized
from app.models import User
from app.security import create_access_token, hash_password, verify_password


def register_user(db: Session, name: str, email: str, password: str) -> User:
    existing = db.query(User).filter(User.email == email.lower().strip()).first()
    if existing:
        raise Conflict("An account with this email already exists")
    user = User(
        name=name.strip(),
        email=email.lower().strip(),
        password_hash=hash_password(password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, email: str, password: str) -> tuple[User, str]:
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user or not verify_password(password, user.password_hash):
        raise Unauthorized("Invalid email or password")
    token = create_access_token(user)
    return user, token


def update_profile(db: Session, user: User, data: dict) -> User:
    for key, value in data.items():
        if value is not None:
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user
