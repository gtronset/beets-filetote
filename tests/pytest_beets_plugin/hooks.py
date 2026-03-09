"""Pytest hooks for pytest-beets-plugin.

Registers custom markers and auto-skip logic for platform feature
requirements (symlinks, hardlinks, reflinks, Platform, etc.).
"""

import pytest

from ._features import HAVE_HARDLINK, HAVE_REFLINK, HAVE_SYMLINK, PLATFORM

_FEATURE_MARKERS: dict[str, tuple[bool, str]] = {
    "needs_symlink": (HAVE_SYMLINK, "no symlink support on this platform"),
    "needs_hardlink": (HAVE_HARDLINK, "no hardlink support on this platform"),
    "needs_reflink": (HAVE_REFLINK, "no reflink support on this platform"),
    "skip_win32": (PLATFORM != "win32", "not supported on win32"),
}


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    for name, (_, description) in _FEATURE_MARKERS.items():
        config.addinivalue_line("markers", f"{name}: {description}")


def pytest_collection_modifyitems(
    _config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Auto-skip tests marked with unavailable feature requirements."""
    for item in items:
        for name, (available, reason) in _FEATURE_MARKERS.items():
            if name in item.keywords and not available:
                item.add_marker(pytest.mark.skip(reason=reason))
