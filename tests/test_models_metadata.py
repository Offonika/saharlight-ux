from services.api.app.diabetes.models import metadata


def test_models_metadata_contains_expected_tables() -> None:
    assert "users" in metadata.tables
    assert "profiles" in metadata.tables
