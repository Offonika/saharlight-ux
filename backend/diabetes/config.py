from backend import config as _config

__all__ = [name for name in dir(_config) if not name.startswith("_")]


def __getattr__(name: str):  # pragma: no cover - simple proxy
    return getattr(_config, name)
