"""Compatibility layer for legacy backend imports.

This package provides a thin wrapper that redirects imports from the old
``backend`` modules to their new locations inside ``services.api.app``.
It allows existing code to continue using the old import paths while the
project is migrated to the new structure.
"""

from __future__ import annotations

import importlib
import sys
from typing import Dict

# Base package for the new FastAPI application
_TARGET_BASE = "services.api.app"

# Map legacy module paths to their new equivalents. Expand this map as needed
# whenever additional compatibility redirects are required.
_IMPORT_MAP: Dict[str, str] = {
    "backend.main": f"{_TARGET_BASE}.main",
    "backend.config": f"{_TARGET_BASE}.config",
    "backend.schemas": f"{_TARGET_BASE}.schemas",
    "backend.services": f"{_TARGET_BASE}.services",
    "backend.diabetes": f"{_TARGET_BASE}.diabetes",
    "backend.middleware": f"{_TARGET_BASE}.middleware",
    "backend.legacy": f"{_TARGET_BASE}.legacy",
}

# Preload and register all mapped modules so ``import backend.<module>``
# transparently provides the new implementations.
for legacy_name, actual_name in _IMPORT_MAP.items():
    sys.modules[legacy_name] = importlib.import_module(actual_name)

# Finally, alias the ``backend`` package itself to the new base package so that
# ``import backend`` gives access to the new FastAPI application package.
_target_pkg = importlib.import_module(_TARGET_BASE)
sys.modules[__name__] = _target_pkg
