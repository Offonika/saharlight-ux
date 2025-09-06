import pytest
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
import importlib
from services.api.app.diabetes.services.db import Base, User, Profile

profile_api = importlib.import_module(
    "services.api.app.diabetes.handlers.profile.api"
)


@pytest.fixture()
def session_factory() -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession: sessionmaker[Session] = sessionmaker(
        bind=engine, autoflush=False, autocommit=False
    )
    try:
        yield TestSession
    finally:
        engine.dispose()


def test_profile_timezone_auto_off(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Profile(telegram_id=1, timezone="UTC", timezone_auto=True))
        session.commit()
        profile_api.set_timezone(session, 1, "Europe/Moscow", auto=False)

    with session_factory() as session:
        profile = session.get(Profile, 1)
        assert profile is not None
        assert profile.timezone == "Europe/Moscow"
        assert profile.timezone_auto is False
