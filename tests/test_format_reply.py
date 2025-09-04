from services.api.app.diabetes.services.gpt_client import format_reply


def test_format_reply_truncates_and_splits() -> None:
    text = "one\n\n" + "x" * 900 + "\n\n\nthree"
    result = format_reply(text, max_len=10)
    assert result == "one\n\n" + "x" * 10 + "\n\nthree"
