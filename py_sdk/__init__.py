"""Helper package to expose diabetes_sdk under py_sdk namespace."""
import importlib
import sys
from pathlib import Path

_pkg_path = Path(__file__).resolve().parent.parent / "libs" / "py-sdk"
_pkg_abs = _pkg_path.resolve()
if _pkg_abs.is_dir() and str(_pkg_abs) not in sys.path:
    sys.path.append(str(_pkg_abs))

diabetes_sdk = importlib.import_module("diabetes_sdk")
sys.modules[__name__ + ".diabetes_sdk"] = diabetes_sdk

__all__ = ["diabetes_sdk"]
