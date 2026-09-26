import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import ModelVersion, User
from app.security import create_access_token, hash_password
from ml.registry import registry

# Create an in-memory SQLite database for test isolation
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    Base.metadata.create_all(bind=test_engine)
    # Ensure active model is loaded in registry from the real artifacts for predictions
    db = TestingSessionLocal()
    try:
        # Check if real DB or artifacts has active model
        if not registry.has_active():
            # If not in registry, look in disk
            from app.config import settings
            # Check if artifact v1 exists
            v1_dir = settings.artifact_path / "v1"
            if v1_dir.exists():
                registry.reload(1, v1_dir)
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def normal_user(db_session: Session):
    user = User(
        name="Test User",
        email="testuser@example.com",
        password_hash=hash_password("Password123!"),
        role="user",
        gender="female",
        age=26,
        height_cm=165.0,
        weight_kg=60.0,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_user(db_session: Session):
    user = User(
        name="Other User",
        email="other@example.com",
        password_hash=hash_password("Password123!"),
        role="user",
        gender="male",
        age=35,
        height_cm=180.0,
        weight_kg=78.0,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session):
    admin = User(
        name="Admin User",
        email="admin_test@example.com",
        password_hash=hash_password("AdminPass123!"),
        role="admin",
        gender="male",
        age=40,
        height_cm=175.0,
        weight_kg=75.0,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def user_token(normal_user: User):
    return create_access_token(normal_user)


@pytest.fixture
def other_token(other_user: User):
    return create_access_token(other_user)


@pytest.fixture
def admin_token(admin_user: User):
    return create_access_token(admin_user)
