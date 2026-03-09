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
from .assertions import AssertionsMixin, BeetsAssertions
from .logging import (
    ListLogHandler,
    capture_beets_log,
    capture_log_with_traceback,
    install_beets_log_fix,
)
from .media import MediaCreator, MediaSetup
from .plugin_fixture import BeetsPluginFixture
from .plugin_lifecycle import (
    _activate_plugins,
    _clear_plugin_state,
    _deactivate_plugins,
    _load_module_from_file,
    _load_plugin_class,
    load_plugin_source,
)
from .utils import (
    PROJECT_ROOT,
    RESOURCES_DIR,
    SAMPLE_MEDIA_FILES,
    BeetsTestUtils,
    HelperUtils,
)

__all__ = [
    "HAVE_HARDLINK",
    "HAVE_REFLINK",
    "HAVE_SYMLINK",
    "PLATFORM",
    "PROJECT_ROOT",
    "RESOURCES_DIR",
    "SAMPLE_MEDIA_FILES",
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
    "_activate_plugins",
    "_clear_plugin_state",
    "_deactivate_plugins",
    "_load_module_from_file",
    "_load_plugin_class",
    "capture_beets_log",
    "capture_log_with_traceback",  # Legacy (deprecated)
    "install_beets_log_fix",
    "load_plugin_source",
]
