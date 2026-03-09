"""Backward-compatible shim for beets-filetote tests.

All implementations have moved to ``tests.pytest_beets_plugin``.
This module re-exports them for existing unittest-based tests.
Remove this file once all tests are migrated to native pytest style.
"""

# Re-export everything that existing tests import from here
from .pytest_beets_plugin.assertions import (  # noqa: F401
    BeetsAssertions,
)

# Backward-compatible aliases
from .pytest_beets_plugin.helper import (  # noqa: F401
    BeetsTestUtils as HelperUtils,
)

# Re-export the legacy class for existing unittest-based tests
from .pytest_beets_plugin.helper import (
    # PROJECT_ROOT,
    # RSRC,
    # RSRC_TYPES,
    # Assertions,
    # BeetsTestUtils,
    FiletoteTestCase,
    # ListLogHandler,
    MediaSetup,
    # _import_local_plugin,
    # _load_module_from_path,
    # capture_beets_log,
    capture_log_with_traceback,
    import_plugin_module_statically,
)

# from .pytest_beets_plugin.plugin_fixture import (
#     BeetsPluginFixture,
# )

__all__ = [
    "FiletoteTestCase",
    "MediaSetup",
    "capture_log_with_traceback",
    "import_plugin_module_statically",
]
