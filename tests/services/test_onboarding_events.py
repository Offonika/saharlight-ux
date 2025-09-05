import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.api.app.diabetes.services.db import Base
from services.api.app.models.onboarding_event import OnboardingEvent
from services.api.app.services.onboarding_events import log_onboarding_event


def test_log_onboarding_event_persists_event() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        log_onboarding_event(
            session, 1, "onboarding_started", step="0", meta={"a": 1}, variant="v1"
        )
        ev = session.query(OnboardingEvent).one()
        assert ev.user_id == 1
        assert ev.event == "onboarding_started"
        assert ev.step == "0"
        assert ev.meta_json == {"a": 1}
        assert ev.variant == "v1"


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({"step": "1"}, {"step": "1", "meta_json": None, "variant": None}),
        ({"meta": {"b": 2}}, {"step": None, "meta_json": {"b": 2}, "variant": None}),
        ({"variant": "v2"}, {"step": None, "meta_json": None, "variant": "v2"}),
    ],
)
def test_log_onboarding_event_optional_fields(
    kwargs: dict[str, object], expected: dict[str, object]
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        log_onboarding_event(session, 1, "evt", **kwargs)
        ev = session.query(OnboardingEvent).one()
        assert ev.step == expected["step"]
        assert ev.meta_json == expected["meta_json"]
        assert ev.variant == expected["variant"]
