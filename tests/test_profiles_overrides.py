import pytest
import services.api.app.profiles as profiles


class DummyCtx:
    def __init__(self, user_data: dict[str, object]) -> None:
        self.user_data = user_data


@pytest.mark.asyncio
async def test_get_profile_for_user_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get_json(path: str) -> dict[str, object]:
        assert path == "/profile/self"
        return {
            "therapyType": "bolus",
            "rapidInsulinType": "aspart",
            "carbUnits": "grams",
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
        "age_group": "adult",
        "diabetes_type": "unknown",
        "learning_level": "expert",
    }
