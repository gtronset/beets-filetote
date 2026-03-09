"""Pytest configuration for beets-filetote tests.

Imports fixtures from the ``pytest_beets_plugin`` package so they are
available to all test modules.
"""

from .pytest_beets_plugin.fixtures import (  # noqa: F401
    beets_plugin_env,
)
from .pytest_beets_plugin.hooks import (  # noqa: F401
    pytest_collection_modifyitems,
    pytest_configure,
)
