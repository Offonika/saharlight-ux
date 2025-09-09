from __future__ import annotations

from fastapi import APIRouter, Depends

from ..assistant.repositories.learning_profile import (
    get_learning_profile,
    upsert_learning_profile,
)
from ..schemas.learning_profile import LearningProfileSchema
from ..schemas.user import UserContext
from ..telegram_auth import check_token

router = APIRouter()


@router.get(
    "/learning-profile",
    response_model=LearningProfileSchema,
    response_model_exclude_none=True,
)
async def learning_profile_get(
    user: UserContext = Depends(check_token),
) -> LearningProfileSchema:
    profile = await get_learning_profile(user["id"])
    if profile is None:
        return LearningProfileSchema()
    return LearningProfileSchema.model_validate(profile)


@router.patch(
    "/learning-profile",
    response_model=LearningProfileSchema,
    response_model_exclude_none=True,
)
async def learning_profile_patch(
    data: LearningProfileSchema,
    user: UserContext = Depends(check_token),
) -> LearningProfileSchema:
    await upsert_learning_profile(
        user["id"],
        age_group=data.age_group,
        learning_level=data.learning_level,
        diabetes_type=data.diabetes_type,
    )
    profile = await get_learning_profile(user["id"])
    if profile is None:
        return LearningProfileSchema()
    return LearningProfileSchema.model_validate(profile)
