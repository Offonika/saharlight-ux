from services.api.app.diabetes.models import metadata


def test_models_metadata_contains_expected_tables() -> None:
    assert "users" in metadata.tables
    assert "profiles" in metadata.tables



def test_models_exports_metadata() -> None:
    from services.api.app.diabetes import models
    assert models.__all__ == ["metadata", "OnboardingState"]
