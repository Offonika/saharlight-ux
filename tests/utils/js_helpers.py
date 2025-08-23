from __future__ import annotations

import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def build_vite_project() -> None:
    """Install dependencies and build the Vite project using npm."""
    subprocess.run([
        "npm",
        "ci",
    ], cwd=ROOT_DIR, check=True)
    subprocess.run(
        ["npm", "--workspace", "services/webapp/ui", "run", "build"],
        cwd=ROOT_DIR,
        check=True,
    )
