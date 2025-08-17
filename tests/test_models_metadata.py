from services.api.app.diabetes import models
from services.api.app.diabetes.services.db import Base


def test_models_metadata_contains_expected_tables() -> None:
    assert "users" in models.metadata.tables
    assert "profiles" in models.metadata.tables


def test_models_exports_metadata() -> None:
    assert models.__all__ == ["metadata"]
    assert models.metadata is Base.metadata

