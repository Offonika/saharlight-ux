from __future__ import annotations

from typing import cast

from sqlalchemy.orm import Session

from ...diabetes.models_learning import LearningUserProfile
from ...diabetes.services.db import SessionLocal, run_db, User
from ...diabetes.services.repository import commit
from ...types import SessionProtocol

__all__ = ["get_learning_profile", "upsert_learning_profile"]


async def get_learning_profile(user_id: int) -> LearningUserProfile | None:
    def _get(session: SessionProtocol) -> LearningUserProfile | None:
        return cast(LearningUserProfile | None, session.get(LearningUserProfile, user_id))

    return await run_db(_get, sessionmaker=SessionLocal)


async def upsert_learning_profile(
    user_id: int,
    *,
    age_group: str | None = None,
    learning_level: str | None = None,
    diabetes_type: str | None = None,
) -> None:
    def _upsert(session: SessionProtocol) -> None:
        sess = cast(Session, session)
        profile = cast(LearningUserProfile | None, sess.get(LearningUserProfile, user_id))
        if profile is None:
            if sess.get(User, user_id) is None:
                raise RuntimeError("User is not registered. Please register.")
            profile = LearningUserProfile(
                user_id=user_id,
                age_group=age_group,
                learning_level=learning_level,
                diabetes_type=diabetes_type,
            )
            sess.add(profile)
        else:
            if age_group is not None:
                profile.age_group = age_group
            if learning_level is not None:
                profile.learning_level = learning_level
            if diabetes_type is not None:
                profile.diabetes_type = diabetes_type
        commit(sess)

    await run_db(_upsert, sessionmaker=SessionLocal)
