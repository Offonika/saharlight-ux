import pytest
from urllib.parse import urlparse

import services.api.app.diabetes.utils.ui as ui


def test_timezone_button_webapp_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Timezone button should open webapp path for timezone detection."""
    monkeypatch.setenv("WEBAPP_URL", "https://example.com")

    button = ui.build_timezone_webapp_button()
    assert button is not None
    web_app = button.web_app
    assert web_app is not None
    assert urlparse(web_app.url).path == "/timezone"
