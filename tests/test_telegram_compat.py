from telegram.ext import ApplicationBuilder


def test_application_builder_build() -> None:
    import importlib

    importlib.import_module("services.api.app")

    app = ApplicationBuilder().token("TESTTOKEN").build()
    assert app is not None
