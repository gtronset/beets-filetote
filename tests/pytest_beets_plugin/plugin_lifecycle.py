"""Plugin loading and unloading utilities for beets plugin tests."""

# ruff: noqa: SLF001

from __future__ import annotations

import logging
import sys

from typing import TYPE_CHECKING, Any

from beets import config, plugins

from ._loader import _import_local_plugin
from .utils import PROJECT_ROOT

log = logging.getLogger("beets")

if TYPE_CHECKING:
    from pathlib import Path


def _load_plugins(
    other_plugins: list[str] | None = None,
    *,
    project_root: Path = PROJECT_ROOT,
) -> None:
    """Load filetote (and optional stub plugins) into the beets plugin system."""
    other_plugins = other_plugins or []
    plugin_list: list[str] = ["filetote"]
    plugin_class_list: list[Any] = []

    filetote_path = project_root / "beetsplug/filetote.py"
    filetote_class = _import_local_plugin(
        filetote_path, "FiletotePlugin", "beetsplug.filetote"
    )
    plugin_class_list.append(filetote_class)

    stub_map: dict[str, tuple[str, str]] = {
        "audible": ("tests/stubs/audible.py", "Audible"),
        "convert": ("tests/stubs/convert.py", "ConvertPlugin"),
        "inline": ("tests/stubs/inline.py", "InlinePlugin"),
    }

    for other_plugin in other_plugins:
        if other_plugin in stub_map:
            stub_path, class_name = stub_map[other_plugin]
            abs_stub_path = project_root / stub_path
            plugin_class = _import_local_plugin(
                abs_stub_path, class_name, f"beetsplug.{other_plugin}"
            )
            plugin_class_list.append(plugin_class)
            plugin_list.append(other_plugin)
        else:
            msg = f"Attempt to load unknown plugin: {other_plugin}"
            raise ValueError(msg)

    plugins._classes = set(plugin_class_list)
    config["plugins"] = plugin_list
    plugins.load_plugins()


def _unload_plugins() -> None:
    """Unload all plugins and clean up global state."""
    config["plugins"] = []

    if plugins._instances:
        classes = list(plugins._classes)
        for plugin_class in classes:
            if plugin_class.listeners:
                for event in list(plugin_class.listeners):
                    plugin_class.listeners[event].clear()
            instances = plugins._instances
            plugins._instances = [
                inst for inst in instances if not isinstance(inst, plugin_class)
            ]

    for modname in list(sys.modules):
        if modname.startswith(("beetsplug.filetote", "beetsplug.audible")):
            del sys.modules[modname]


def _teardown_plugin_state() -> None:
    """Clear global plugin registries."""
    attrs_to_clear = [
        ("beets.plugins", "_instances"),
        ("beets.plugins", "_classes"),
        ("beets.plugins", "_event_listeners"),
        ("beets.plugins.BeetsPlugin", "listeners"),
        ("beets.plugins.BeetsPlugin", "_raw_listeners"),
        ("beets.plugins.BeetsPlugin", "_raw_listeners"),
    ]

    for obj_path, attr in attrs_to_clear:
        try:
            if "." in obj_path:
                module_path, class_name = obj_path.rsplit(".", 1)
                module = sys.modules[module_path]
                obj = getattr(module, class_name)
            else:
                obj = sys.modules[obj_path]
        except (KeyError, AttributeError):
            # If the module or attribute doesn't exist, skip it.
            log.warning("Could not resolve path `%s` for teardown.", obj_path)
            continue

        if hasattr(obj, attr):
            val = getattr(obj, attr)
            if val is not None and hasattr(val, "clear"):
                val.clear()
