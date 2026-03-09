"""Plugin loading utilities for beets plugin tests."""

from __future__ import annotations

import importlib.util
import sys

from typing import TYPE_CHECKING, cast

from .utils import PROJECT_ROOT

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType

    from beets.plugins import BeetsPlugin


def _load_module_from_path(module_name: str, module_path: str | Path) -> ModuleType:
    """Core helper to load a module from a specific file path."""
    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
    if not (spec and spec.loader):
        msg = f"Could not create module spec for {module_name} at {module_path}"
        raise ImportError(msg)

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def import_plugin_module_statically(module_name: str) -> ModuleType:
    """Load a plugin module directly from its source file.

    Useful for unit tests that need to import a module statically,
    bypassing the ``beetsplug`` package namespace.
    """
    module_path: Path = PROJECT_ROOT / f"beetsplug/{module_name}.py"
    return _load_module_from_path(module_name, module_path)


def _import_local_plugin(
    module_path: Path,
    class_name: str,
    module_name: str,
) -> type[BeetsPlugin]:
    """Dynamically import a plugin class from a local file."""
    import beetsplug  # Lazy import to avoid loading before typeguard # noqa: PLC0415

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    module: ModuleType = _load_module_from_path(module_name, module_path)

    # Patch beetsplug namespace if needed
    namespace, _, submodule = module_name.partition(".")
    if namespace == "beetsplug" and submodule:
        setattr(beetsplug, submodule, module)
        sys.modules[f"beetsplug.{submodule}"] = module
    return cast("type[BeetsPlugin]", getattr(module, class_name))
