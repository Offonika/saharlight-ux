import pytest
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from unittest.mock import MagicMock

import importlib

from services.api.app.diabetes.services.db import Base, User, Profile
from services.api.app.diabetes.services.repository import CommitError

profile_api = importlib.import_module("services.api.app.diabetes.handlers.profile.api")


@pytest.fixture()
def session_factory() -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession: sessionmaker[Session] = sessionmaker(
        bind=engine, autoflush=False, autocommit=False
    )
    try:
        yield TestSession
    finally:
        engine.dispose()


def test_post_profile_success() -> None:
    class DummyAPI:
        def __init__(self) -> None:
            self.called_with: object | None = None

        def profiles_post(self, profile: object) -> None:
            self.called_with = profile

    class DummyProfile:
        def __init__(
            self,
            telegram_id: int,
            icr: float,
            cf: float,
            target: float,
            low: float,
            high: float,
        ) -> None:
            self.telegram_id = telegram_id
            self.icr = icr
            self.cf = cf
            self.target = target
            self.low = low
            self.high = high

    api = DummyAPI()
    ok, err = profile_api.post_profile(
        api,
        Exception,
        DummyProfile,
        1,
        1.0,
        2.0,
        3.0,
        4.0,
        5.0,
    )
    assert ok is True and err is None
    assert isinstance(api.called_with, DummyProfile)
    assert api.called_with.icr == 1.0


def test_post_profile_error() -> None:
    class ApiExc(Exception):
        pass

    class DummyAPI:
        def profiles_post(self, profile: object) -> None:
            raise ApiExc("boom")

    class DummyProfile:
        def __init__(
            self,
            telegram_id: int,
            icr: float,
            cf: float,
            target: float,
            low: float,
            high: float,
        ) -> None:
            self.telegram_id = telegram_id
            self.icr = icr
            self.cf = cf
            self.target = target
            self.low = low
            self.high = high

    ok, err = profile_api.post_profile(
        DummyAPI(),
        ApiExc,
        DummyProfile,
        1,
        1.0,
        2.0,
        3.0,
        4.0,
        5.0,
    )
    assert ok is False
    assert err == "boom"


def test_save_profile_persists(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.commit()
        ok = profile_api.save_profile(
            session,
            1,
            10.0,
            2.0,
            5.0,
            3.0,
            8.0,
            sos_contact="911",
            sos_alerts_enabled=False,
        )
        assert ok is True

    with session_factory() as session:
        prof = session.get(Profile, 1)
        assert prof is not None
        assert prof.icr == 10.0
        assert prof.cf == 2.0
        assert prof.target_bg == 5.0
        assert prof.low_threshold == 3.0
        assert prof.high_threshold == 8.0
        assert prof.sos_contact == "911"
        assert prof.sos_alerts_enabled is False


def test_save_profile_commit_failure(
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> None:
    def fail_commit(session: object) -> bool:
        raise CommitError

    monkeypatch.setattr(profile_api, "commit", fail_commit)
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.commit()
        ok = profile_api.save_profile(session, 1, 1.0, 1.0, 1.0, 1.0, 1.0)
        assert ok is False

    with session_factory() as session:
        prof = session.get(Profile, 1)
        assert prof is None


def test_local_profiles_post_failure(
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> None:
    api = profile_api.LocalProfileAPI(session_factory)
    monkeypatch.setattr(profile_api, "save_profile", lambda *a, **k: False)
    with pytest.raises(profile_api.ProfileSaveError):
        api.profiles_post(profile_api.LocalProfile(telegram_id=1))


def test_local_profiles_roundtrip(session_factory: sessionmaker[Session]) -> None:
    api = profile_api.LocalProfileAPI(session_factory)

    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.commit()

    profile = profile_api.LocalProfile(
        telegram_id=1,
        icr=1.0,
        cf=2.0,
        target=3.0,
        low=4.0,
        high=5.0,
        sos_contact="112",
        sos_alerts_enabled=False,
    )
    api.profiles_post(profile)
    fetched = api.profiles_get(1)
    assert fetched is not None
    assert fetched.sos_contact == "112"
    assert fetched.sos_alerts_enabled is False


def test_set_timezone_persists(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.commit()
        found, ok = profile_api.set_timezone(session, 1, "Europe/Moscow")
        assert (found, ok) == (True, True)

    with session_factory() as session:
        user = session.get(User, 1)
        assert user is not None
        assert user.timezone == "Europe/Moscow"


def test_set_timezone_commit_failure(
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> None:
    def fail_commit(session: object) -> bool:
        raise CommitError

    monkeypatch.setattr(profile_api, "commit", fail_commit)
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.commit()
        found, ok = profile_api.set_timezone(session, 1, "Europe/Moscow")
        assert (found, ok) == (True, False)

    with session_factory() as session:
        user = session.get(User, 1)
        assert user is not None
        assert user.timezone == "UTC"


def test_set_timezone_user_missing(
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> None:
    commit_mock = MagicMock(return_value=True)
    monkeypatch.setattr(profile_api, "commit", commit_mock)
    with session_factory() as session:
        found, ok = profile_api.set_timezone(session, 999, "UTC")
        assert (found, ok) == (False, False)
        commit_mock.assert_not_called()
