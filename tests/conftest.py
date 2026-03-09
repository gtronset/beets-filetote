"""Pytest configuration for beets-filetote tests.

Imports fixtures from the ``pytest_beets_plugin`` package so they are
available to all test modules.
"""

from .pytest_beets_plugin.conftest import (  # noqa: F401
    _beets_config,
    _beets_io,
    _beets_lib,
    _beets_plugin_lifecycle,
    beets_plugin_env,
    pytest_collection_modifyitems,
    pytest_configure,
)
