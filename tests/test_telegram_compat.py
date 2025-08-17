import services.api.app  # noqa: F401  # ensures compatibility patch is applied
from telegram.ext import ApplicationBuilder


def test_application_builder_build() -> None:
    app = ApplicationBuilder().token("TESTTOKEN").build()
    assert app is not None
