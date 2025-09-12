from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from services.api.app.main import app


def test_shutdown_clients_dispose() -> None:
    with patch(
        "services.api.app.main.dispose_geo_client",
        new_callable=AsyncMock,
    ) as dispose_geo, patch(
        "services.api.app.main.dispose_http_client",
        new_callable=AsyncMock,
    ) as dispose_http, patch(
        "services.api.app.main.dispose_openai_clients",
        new_callable=AsyncMock,
    ) as dispose_clients:
        with TestClient(app):
            pass
        dispose_geo.assert_awaited_once()
        dispose_http.assert_awaited_once()
        dispose_clients.assert_awaited_once()
