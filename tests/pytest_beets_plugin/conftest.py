"""Auto-discovered fixtures for the pytest-beets-plugin package."""

from .fixtures import (
    _beets_config,
    _beets_io,
    _beets_lib,
    _beets_plugin_lifecycle,
    beets_plugin_env,
)
from .hooks import (
    pytest_collection_modifyitems,
    pytest_configure,
)

__all__ = [
    "_beets_config",
    "_beets_io",
    "_beets_lib",
    "_beets_plugin_lifecycle",
    "beets_plugin_env",
    "pytest_collection_modifyitems",
    "pytest_configure",
]
