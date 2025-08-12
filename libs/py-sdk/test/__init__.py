import sys
from pathlib import Path

# Ensure libs/py-sdk is on sys.path for diabetes_sdk package
sys.path.append(str(Path(__file__).resolve().parents[1]))
