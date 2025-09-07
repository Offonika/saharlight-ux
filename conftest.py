from __future__ import annotations

from argparse import Namespace

import pytest
from _pytest.config import Config


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: Config) -> None:
    if not config.pluginmanager.hasplugin("pytest_cov"):
        return
    option: Namespace = config.option
    if getattr(option, "cov", None) is None:
        setattr(option, "cov", ["services.api.app.diabetes"])
    if getattr(option, "cov_report", None) is None:
        setattr(option, "cov_report", ["term-missing"])
    if getattr(option, "cov_fail_under", None) is None:
        setattr(option, "cov_fail_under", 85)
