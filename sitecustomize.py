"""Customize Python startup behavior for the project.

The project imports ``services.api.app`` at interpreter start to apply a
Telegram compatibility patch.  Importing the package too early prevents test
coverage from measuring the module, so skip the import when running tests.
The tests themselves import ``services.api.app`` once coverage has started.
"""

import os

if "PYTEST_CURRENT_TEST" not in os.environ:
    import services.api.app  # noqa: F401  # applies Telegram compatibility patch
