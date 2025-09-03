from services.api.app.utils.ab import choose_variant


def test_choose_variant_is_deterministic() -> None:
    assert choose_variant(123) == choose_variant(123)
    assert choose_variant(123) in {"A", "B"}


def test_choose_variant_distribution() -> None:
    a = choose_variant(1)
    b = choose_variant(2)
    assert a in {"A", "B"}
    assert b in {"A", "B"}
    assert a != b
