"""pytest-beets-plugin: Test helpers and fixtures for beets plugin development."""

from .assertions import AssertionsMixin, BeetsAssertions
from .helper import (
    PROJECT_ROOT,
    RSRC,
    RSRC_TYPES,
    Assertions,
    BeetsTestUtils,
    FiletoteTestCase,
    HelperUtils,
    ListLogHandler,
    MediaSetup,
    _import_local_plugin,
    _load_module_from_path,
    capture_beets_log,
    capture_log_with_traceback,
    import_plugin_module_statically,
)
from .plugin_fixture import BeetsPluginFixture

__all__ = [
    "PROJECT_ROOT",
    "RSRC",
    "RSRC_TYPES",
    "Assertions",
    "AssertionsMixin",  # Legacy (deprecated)
    "BeetsAssertions",
    "BeetsPluginFixture",
    "BeetsTestUtils",
    "FiletoteTestCase",  # Legacy (deprecated)
    "HelperUtils",  # Legacy (deprecated)
    "ListLogHandler",
    "MediaSetup",
    "_import_local_plugin",
    "_load_module_from_path",
    "capture_beets_log",
    "capture_log_with_traceback",  # Legacy (deprecated)
    "import_plugin_module_statically",
]
