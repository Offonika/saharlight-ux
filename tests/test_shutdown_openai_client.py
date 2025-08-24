from unittest.mock import patch

from fastapi.testclient import TestClient

from services.api.app.main import app


def test_shutdown_openai_client_disposes() -> None:
    with patch("services.api.app.main.dispose_http_client") as dispose:
        with TestClient(app):
            pass
        dispose.assert_called_once()
