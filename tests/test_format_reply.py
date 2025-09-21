import pytest

from services.api.app.diabetes.services.gpt_client import format_reply


def test_format_reply_truncates_and_splits() -> None:
    text = "one\n\n" + "x" * 900 + "\n\n\nthree"
    result = format_reply(text, max_len=10)
    assert result == "one\n\n" + "x" * 10 + "\n\nthree"


def test_format_reply_truncates_to_default_limit() -> None:
    text = "a" * 900 + "\n\n" + "b" * 1000
    result = format_reply(text)
    assert result == "a" * 800 + "\n\n" + "b" * 800


@pytest.mark.parametrize("max_len", [0, -1])
def test_format_reply_raises_for_non_positive_max_len(max_len: int) -> None:
    with pytest.raises(ValueError, match="max_len must be positive"):
        format_reply("text", max_len=max_len)
