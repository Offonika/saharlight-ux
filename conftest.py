from __future__ import annotations

import os
from argparse import Namespace

import pytest
from _pytest.config import Config


# Ensure pytest runs against the dedicated test environment file.
#
# Developers often keep a populated `.env` with production credentials
# locally.  Loading it inside the test suite leads to flaky behaviour where
# tests observe real tokens or URLs instead of the lightweight fixtures from
# `.env.test`.  This environment variable is consulted by the settings module
# to pick the configuration source.
os.environ.setdefault("SAHARLIGHT_ENV_FILE", ".env.test")


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
