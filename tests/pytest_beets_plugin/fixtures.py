"""Pytest fixtures for beets plugin tests."""

# ruff: noqa: SLF001

import logging

from collections.abc import Generator
from pathlib import Path

import pytest

from beets import config, library, util

from ._io import DummyIO
from .plugin_fixture import BeetsPluginFixture
from .plugin_lifecycle import _clear_plugin_state, _deactivate_plugins
from .utils import BeetsTestUtils

log = logging.getLogger("beets")


@pytest.fixture
def _beets_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Isolate beets global configuration for a single test."""
    config.sources = []
    config.read(user=False, defaults=True)

    config["statefile"] = str(tmp_path / "state.pickle")
    config["library"] = str(tmp_path / "library.db")
    config["directory"] = str(tmp_path / "libdir")

    monkeypatch.setenv("HOME", str(tmp_path))

    yield

    config.clear()


@pytest.fixture
def _beets_io() -> Generator[DummyIO]:
    """Install a DummyIO that captures stdin/stdout."""
    io = DummyIO()
    io.install()
    yield io
    io.restore()


@pytest.fixture
def _beets_lib(
    tmp_path: Path, _beets_config: None
) -> Generator[tuple[library.Library, Path]]:
    """Create a beets Library backed by a temporary database.

    Returns a ``(lib, lib_dir)`` tuple. Depends on ``_beets_config`` to
    ensure config is isolated before the library is created.
    Closes the library on teardown.
    """
    helpers = BeetsTestUtils()

    lib_dir = tmp_path / "testlib_dir"
    lib_dir.mkdir(parents=True, exist_ok=True)

    lib_db = tmp_path / "testlib.blb"
    lib = library.Library(util.bytestring_path(lib_db))
    lib.directory = util.bytestring_path(lib_dir)
    lib.path_formats = [
        ("default", helpers.fmt_path("$artist", "$album", "$title")),
        ("singleton:true", helpers.fmt_path("singletons", "$title")),
        ("comp:true", helpers.fmt_path("compilations", "$album", "$title")),
    ]

    yield lib, lib_dir

    lib._close()


@pytest.fixture
def _beets_plugin_lifecycle() -> Generator[None]:
    """Ensure plugins are cleaned up after each test."""
    yield
    _deactivate_plugins()
    _clear_plugin_state()


# ---------------------------------------------------------------------------
# Main entry-point fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def beets_plugin_env(
    tmp_path: Path,
    _beets_lib: tuple[library.Library, Path],
    _beets_io: DummyIO,
    _beets_plugin_lifecycle: None,
) -> BeetsPluginFixture:
    """The primary fixture for beets plugin tests.

    Composes domain fixtures:

    - ``_beets_config`` — config isolation (pulled in via ``_beets_lib``)
    - ``_beets_lib`` — temporary library + database (with teardown)
    - ``_beets_io`` — stdin/stdout capture
    - ``_beets_plugin_lifecycle`` — plugin teardown on exit
    """
    lib, lib_dir = _beets_lib
    import_dir = tmp_path / "testsrc_dir"

    return BeetsPluginFixture(
        tmp_path=tmp_path,
        lib=lib,
        lib_dir=lib_dir,
        import_dir=import_dir,
    )
