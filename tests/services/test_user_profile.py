import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services import db
from services.api.app.diabetes.services import user_profile


@pytest.fixture()
def session_local(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[SASession]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, class_=SASession, autoflush=False, autocommit=False)
    monkeypatch.setattr(db, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(user_profile, "SessionLocal", SessionLocal, raising=False)
    yield SessionLocal
    engine.dispose()


@pytest.mark.asyncio
async def test_save_timezone_persists(session_local: sessionmaker[SASession]) -> None:
    await user_profile.save_timezone(1, "Europe/Moscow", False)
    with session_local() as session:
        profile = session.get(db.Profile, 1)
        user = session.get(db.User, 1)
        assert user is not None
        assert profile is not None
        assert profile.timezone == "Europe/Moscow"
        assert profile.timezone_auto is False
