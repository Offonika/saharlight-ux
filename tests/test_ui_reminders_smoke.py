import threading
import time

import httpx
from uvicorn import Config, Server

import services.api.app.main as server


def _run_server() -> Server:
    config = Config(
        server.app, host="127.0.0.1", port=8001, log_level="info", ws="wsproto"
    )
    srv = Server(config)
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    while not srv.started:
        time.sleep(0.05)
    return srv


def test_reminders_page_smoke() -> None:
    srv = _run_server()
    try:
        resp = httpx.get("http://127.0.0.1:8001/ui/reminders", timeout=5.0)
        assert resp.status_code == 200
        assert "<html" in resp.text.lower()
    finally:
        srv.should_exit = True
