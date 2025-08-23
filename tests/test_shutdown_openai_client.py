from unittest.mock import patch

from services.api.app.main import shutdown_openai_client


async def test_shutdown_openai_client_disposes() -> None:
    with patch("services.api.app.main.dispose_http_client") as dispose:
        await shutdown_openai_client()
        dispose.assert_called_once()
