"""pytest-beets-plugin: Test helpers and fixtures for beets plugin development."""

from ._features import (
    HAVE_HARDLINK,
    HAVE_REFLINK,
    HAVE_SYMLINK,
    PLATFORM,
)
from ._io import DummyIO
from ._item_model import MediaMeta
from ._legacy import FiletoteTestCase
from ._loader import (
    _import_local_plugin,
    _load_module_from_path,
    import_plugin_module_statically,
)
from .assertions import AssertionsMixin, BeetsAssertions
from .logging import (
    ListLogHandler,
    capture_beets_log,
    capture_log_with_traceback,
    install_beets_log_fix,
)
from .media import MediaCreator, MediaSetup
from .plugin_fixture import BeetsPluginFixture
from .plugin_lifecycle import _load_plugins, _teardown_plugin_state, _unload_plugins
from .utils import PROJECT_ROOT, RSRC, RSRC_TYPES, BeetsTestUtils, HelperUtils

__all__ = [
    "HAVE_HARDLINK",
    "HAVE_REFLINK",
    "HAVE_SYMLINK",
    "PLATFORM",
    "PROJECT_ROOT",
    "RSRC",
    "RSRC_TYPES",
    "AssertionsMixin",  # Legacy (deprecated)
    "BeetsAssertions",
    "BeetsPluginFixture",
    "BeetsTestUtils",
    "DummyIO",
    "FiletoteTestCase",  # Legacy (deprecated)
    "HelperUtils",  # Legacy (deprecated)
    "ListLogHandler",
    "MediaCreator",
    "MediaMeta",
    "MediaSetup",
    "_import_local_plugin",
    "_load_module_from_path",
    "_load_plugins",
    "_teardown_plugin_state",
    "_unload_plugins",
    "capture_beets_log",
    "capture_log_with_traceback",  # Legacy (deprecated)
    "import_plugin_module_statically",
    "install_beets_log_fix",
]
