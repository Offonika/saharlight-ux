from diabetes_sdk import Configuration
from diabetes_sdk.api import default_api


def run() -> None:
  """Entry point for the worker service."""
  api = default_api.DefaultApi(configuration=Configuration())
  print("Worker started. API client ready:", api)


if __name__ == "__main__":
  run()
