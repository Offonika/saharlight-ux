import httpx
import pytest

import services.api.app.profiles as profiles


class DummyCtx:
    def __init__(self, user_data: dict[str, object]) -> None:
        self.user_data = user_data


@pytest.mark.asyncio
async def test_get_profile_for_user_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get_json(path: str, _ctx: object | None = None) -> dict[str, object]:
        if path == "/profile/self":
            return {
                "therapyType": "bolus",
                "rapidInsulinType": "aspart",
                "carbUnits": "grams",
            }
        assert path == "/learning-profile"
        return {
            "age_group": "child",
            "diabetes_type": "T1",
            "learning_level": "novice",
        }

    monkeypatch.setattr(profiles, "get_json", fake_get_json)
    ctx = DummyCtx(
        {"learn_profile_overrides": {"carbUnits": "units", "learning_level": "expert"}}
    )
    result = await profiles.get_profile_for_user(123, ctx)
    assert result == {
        "therapyType": "bolus",
        "rapidInsulinType": "aspart",
        "carbUnits": "units",
        "age_group": "child",
        "diabetes_type": "T1",
        "learning_level": "expert",
    }


@pytest.mark.asyncio
async def test_get_profile_for_user_unauthorized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_json(path: str, _ctx: object | None = None) -> dict[str, object]:
        request = httpx.Request("GET", f"http://example{path}")
        response = httpx.Response(401, request=request)
        raise httpx.HTTPStatusError("unauthorized", request=request, response=response)

    monkeypatch.setattr(profiles, "get_json", fake_get_json)
    ctx = DummyCtx({"learn_profile_overrides": {"learning_level": "expert"}})
    with pytest.raises(httpx.HTTPStatusError):
        await profiles.get_profile_for_user(123, ctx)


@pytest.mark.asyncio
async def test_get_profile_for_user_passes_tg_init_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_json(path: str, ctx: object | None = None) -> dict[str, object]:
        assert isinstance(ctx, DummyCtx)
        assert ctx.user_data["tg_init_data"] == "abc"
        return {}

    monkeypatch.setattr(profiles, "get_json", fake_get_json)
    ctx = DummyCtx({"tg_init_data": "abc"})
    await profiles.get_profile_for_user(1, ctx)
