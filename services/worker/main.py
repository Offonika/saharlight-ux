"""Worker service entry point."""

import sys

try:
  from diabetes_sdk import Configuration
  from diabetes_sdk.api import default_api
except ImportError:
  print(
    "diabetes_sdk is required to run the worker. "
    "Install it with 'pip install diabetes_sdk'."
  )
  sys.exit(1)


def run() -> None:
  """Entry point for the worker service."""
  api = default_api.DefaultApi(configuration=Configuration())
  print("Worker started. API client ready:", api)


if __name__ == "__main__":
  run()
