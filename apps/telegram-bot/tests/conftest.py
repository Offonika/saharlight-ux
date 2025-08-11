import sys
from pathlib import Path

# Ensure the backend package is importable
root_path = Path(__file__).resolve().parents[3]
backend_path = root_path / "backend"
for p in (root_path, backend_path):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
