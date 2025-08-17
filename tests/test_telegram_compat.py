import services.api.app.telegram_compat  # noqa: F401
from telegram.ext import ApplicationBuilder


def test_application_builder_build() -> None:
    app = ApplicationBuilder().token("TESTTOKEN").build()
    assert app is not None
