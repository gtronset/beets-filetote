"""Pytest configuration for beets-filetote tests.

Imports fixtures from the ``pytest_beets_plugin`` package so they are
available to all test modules.
"""

from .pytest_beets_plugin.fixtures import (  # noqa: F401
    beets_config,
    beets_io,
    beets_lib,
    beets_plugin_env,
    beets_plugin_lifecycle,
    import_dir,
    lib_dir,
)
