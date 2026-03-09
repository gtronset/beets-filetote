"""Plugin loading, unloading, and module import utilities for beets plugin tests."""

# ruff: noqa: SLF001

import importlib.util
import logging
import sys

from pathlib import Path
from types import ModuleType
from typing import Any, cast

from beets import config, plugins
from beets.plugins import BeetsPlugin

from .utils import PROJECT_ROOT

log = logging.getLogger("beets")


def _load_module_from_file(module_name: str, module_path: str | Path) -> ModuleType:
    """Core helper to load a module from a specific file path."""
    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
    if not (spec and spec.loader):
        msg = f"Could not create module spec for {module_name} at {module_path}"
        raise ImportError(msg)

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_plugin_source(module_name: str) -> ModuleType:
    """Load a plugin module directly from its source file.

    Useful for unit tests that need to import a module statically,
    bypassing the ``beetsplug`` package namespace.
    """
    module_path: Path = PROJECT_ROOT / f"beetsplug/{module_name}.py"
    return _load_module_from_file(module_name, module_path)


def _load_plugin_class(
    module_path: Path,
    class_name: str,
    module_name: str,
) -> type[BeetsPlugin]:
    """Dynamically import a plugin class from a local file."""
    import beetsplug  # Lazy import to avoid loading before typeguard # noqa: PLC0415

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    module: ModuleType = _load_module_from_file(module_name, module_path)

    # Patch beetsplug namespace if needed
    namespace, _, submodule = module_name.partition(".")
    if namespace == "beetsplug" and submodule:
        setattr(beetsplug, submodule, module)
        sys.modules[f"beetsplug.{submodule}"] = module
    return cast("type[BeetsPlugin]", getattr(module, class_name))


def _activate_plugins(
    other_plugins: list[str] | None = None,
    *,
    project_root: Path = PROJECT_ROOT,
) -> None:
    """Load, register, and configure Filetote (and optional stub plugins)."""
    other_plugins = other_plugins or []
    plugin_list: list[str] = ["filetote"]
    plugin_class_list: list[Any] = []

    filetote_path = project_root / "beetsplug/filetote.py"
    filetote_class = _load_plugin_class(
        filetote_path, "FiletotePlugin", "beetsplug.filetote"
    )
    plugin_class_list.append(filetote_class)

    stub_map: dict[str, tuple[str, str]] = {
        "audible": ("tests/pytest_beets_plugin/stubs/audible.py", "Audible"),
        "convert": ("tests/pytest_beets_plugin/stubs/convert.py", "ConvertPlugin"),
        "inline": ("tests/pytest_beets_plugin/stubs/inline.py", "InlinePlugin"),
    }

    for other_plugin in other_plugins:
        if other_plugin in stub_map:
            stub_path, class_name = stub_map[other_plugin]
            abs_stub_path = project_root / stub_path
            plugin_class = _load_plugin_class(
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


def _deactivate_plugins() -> None:
    """Deregister all plugins, clear listeners, and purge from sys.modules."""
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


def _clear_plugin_state() -> None:
    """Clear global plugin registries (instances, classes, listeners)."""
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
