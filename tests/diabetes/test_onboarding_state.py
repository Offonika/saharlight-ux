from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession, sessionmaker

from services.api.app.diabetes.services import db
from services.api.app.services import onboarding_state


@pytest.fixture()
def session_local(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[SASession]:
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine, class_=SASession)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(db, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(onboarding_state, "SessionLocal", SessionLocal, raising=False)
    yield SessionLocal
    engine.dispose()


@pytest.mark.asyncio
async def test_save_and_load(session_local: sessionmaker[SASession]) -> None:
    await onboarding_state.save_state(1, 2, {"foo": "bar"}, "A")
    state = await onboarding_state.load_state(1)
    assert state is not None
    assert state.step == 2
    assert state.data == {"foo": "bar"}
    assert state.variant == "A"


@pytest.mark.asyncio
async def test_expired_state_removed(session_local: sessionmaker[SASession]) -> None:
    await onboarding_state.save_state(1, 1, {})
    with session_local() as session:
        st = session.get(onboarding_state.OnboardingState, 1)
        assert st is not None
        st.updated_at = datetime.now(timezone.utc) - timedelta(days=15)
        session.commit()
    state = await onboarding_state.load_state(1)
    assert state is None
    with session_local() as session:
        assert session.get(onboarding_state.OnboardingState, 1) is None


@pytest.mark.asyncio
async def test_complete_state_sets_timestamp(session_local: sessionmaker[SASession]) -> None:
    await onboarding_state.save_state(1, 1, {})
    await onboarding_state.complete_state(1)
    state = await onboarding_state.load_state(1)
    assert state is not None
    assert state.completed_at is not None
