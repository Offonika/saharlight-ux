import pytest

import services.api.app.profiles as profiles


class DummyCtx:
    def __init__(self, user_data: dict[str, object]) -> None:
        self.user_data = user_data


@pytest.mark.asyncio
async def test_get_profile_for_user_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get_json(path: str, _ctx: object | None = None) -> dict[str, object]:
        assert path == "/profile/self"
        return {
            "age_group": "child",
            "diabetes_type": "T1",
            "learning_level": "novice",
        }

    monkeypatch.setattr(profiles, "get_json", fake_get_json)
    ctx = DummyCtx(
        {
            "learn_profile_overrides": {"carbUnits": "units", "learning_level": "expert"},
            "tg_init_data": "abc",
        }
    )
    result = await profiles.get_profile_for_user(123, ctx)
    assert result == {
        "carbUnits": "units",
        "age_group": "child",
        "diabetes_type": "T1",
        "learning_level": "expert",
    }


@pytest.mark.asyncio
async def test_get_profile_for_user_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_get_json(path: str, _ctx: object | None = None) -> dict[str, object]:
        raise AssertionError("should not call API without token")

    monkeypatch.setattr(profiles, "get_json", fail_get_json)
    ctx = DummyCtx({"learn_profile_overrides": {"learning_level": "expert"}})
    result = await profiles.get_profile_for_user(123, ctx)
    assert result["learning_level"] == "expert"


@pytest.mark.asyncio
async def test_get_profile_for_user_passes_tg_init_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_json(path: str, ctx: object | None = None) -> dict[str, object]:
        assert path == "/profile/self"
        assert isinstance(ctx, DummyCtx)
        assert ctx.user_data["tg_init_data"] == "abc"
        return {}

    monkeypatch.setattr(profiles, "get_json", fake_get_json)
    ctx = DummyCtx({"tg_init_data": "abc"})
    await profiles.get_profile_for_user(1, ctx)
