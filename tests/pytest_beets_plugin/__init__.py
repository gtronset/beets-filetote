"""pytest-beets-plugin: Test helpers and fixtures for beets plugin development."""

from ._io import DummyIO
from ._item_model import MediaMeta
from .logging import (
    ListLogHandler,
    capture_beets_log,
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
    BeetsTestUtils,
)

__all__ = [
    "BeetsPluginFixture",
    "BeetsTestUtils",
    "DummyIO",
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
    "install_beets_log_fix",
    "load_plugin_source",
]
