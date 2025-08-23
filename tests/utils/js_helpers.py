from __future__ import annotations

import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def build_vite_project() -> None:
    """Install dependencies and build the Vite project using pnpm."""
    subprocess.run([
        "pnpm",
        "install",
    ], cwd=ROOT_DIR, check=True)
    subprocess.run(
        ["pnpm", "--filter", "services/webapp/ui", "run", "build"],
        cwd=ROOT_DIR,
        check=True,
    )
