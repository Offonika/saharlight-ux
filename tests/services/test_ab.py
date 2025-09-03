from services.api.app.utils.ab import choose_variant


def test_choose_variant_stable() -> None:
    assert choose_variant(123) == choose_variant(123)


def test_choose_variant_distribution() -> None:
    variants = {choose_variant(i) for i in range(100)}
    assert variants == {"A", "B"}
