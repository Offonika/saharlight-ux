from dataclasses import dataclass


@dataclass
class Configuration:
    """Basic configuration holder for API client."""

    host: str | None = None
