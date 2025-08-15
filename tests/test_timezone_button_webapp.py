import pytest

import importlib
from urllib.parse import urlparse


def test_timezone_button_webapp_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Timezone button should open webapp path for timezone detection."""
    monkeypatch.setenv("WEBAPP_URL", "https://example.com")

    import services.api.app.config as config
    import services.api.app.diabetes.utils.ui as ui

    importlib.reload(config)
    importlib.reload(ui)

    button = ui.build_timezone_webapp_button()
    assert button is not None
    assert urlparse(button.web_app.url).path == "/ui/timezone"

    monkeypatch.delenv("WEBAPP_URL", raising=False)
    importlib.reload(config)
    importlib.reload(ui)
