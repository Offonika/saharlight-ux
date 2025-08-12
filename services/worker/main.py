"""Worker service entry point."""

import logging
import sys

try:
    from diabetes_sdk import Configuration
    from diabetes_sdk.api import default_api
except ImportError:
    logging.error(
        "diabetes_sdk is required to run the worker. "
        "Install it with 'pip install diabetes_sdk'."
    )
    sys.exit(1)


def run() -> None:
    """Entry point for the worker service."""
    api = default_api.DefaultApi(configuration=Configuration())
    logging.info("Worker started. API client ready: %s", api)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
