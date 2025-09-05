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
