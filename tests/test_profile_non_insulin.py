import pytest
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.diabetes.services.db import User
from services.api.app.schemas.profile import ProfileSchema
from services.api.app.services import profile as profile_service


@pytest.mark.asyncio
@pytest.mark.parametrize("therapy_type", ["tablets", "none"])
async def test_save_profile_allows_non_insulin(
    therapy_type: str, in_memory_db: sessionmaker[Session]
) -> None:
    with in_memory_db() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    data = ProfileSchema(
        telegramId=1,
        target=5.0,
        low=4.0,
        high=6.0,
        therapyType=therapy_type,
    )

    await profile_service.save_profile(data)
    prof = await profile_service.get_profile(1)
    assert prof.icr is None
    assert prof.cf is None
