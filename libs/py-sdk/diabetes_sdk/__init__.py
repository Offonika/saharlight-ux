"""Minimal SDK facade for diabetes assistant API."""

from .api import default_api
from .api_client import ApiClient
from .configuration import Configuration
from .exceptions import ApiException

__all__ = [
    "Configuration",
    "default_api",
    "ApiClient",
    "ApiException",
]
