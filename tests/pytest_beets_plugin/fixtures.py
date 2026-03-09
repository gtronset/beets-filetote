"""Pytest fixtures for beets plugin tests."""

# from __future__ import annotations

# ruff: noqa: SLF001

import logging

from collections.abc import Generator
from pathlib import Path

import pytest

from beets import config, library, util

from ._io import DummyIO
from .plugin_fixture import BeetsPluginFixture
from .plugin_lifecycle import _teardown_plugin_state, _unload_plugins
from .utils import BeetsTestUtils

log = logging.getLogger("beets")

# Path to the project root (two levels up from this file).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Low-level fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def beets_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
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
def beets_io() -> Generator[DummyIO]:
    """Install a DummyIO that captures stdin/stdout."""
    io = DummyIO()
    io.install()
    yield io
    io.restore()


# ---------------------------------------------------------------------------
# Library / directory fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def lib_dir(tmp_path: Path) -> Path:
    """Create and return the library directory."""
    d = tmp_path / "testlib_dir"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def beets_lib(
    tmp_path: Path, lib_dir: Path, _beets_config: None
) -> Generator[library.Library]:
    """Create a beets Library backed by a temporary database."""
    helpers = BeetsTestUtils()
    lib_db = tmp_path / "testlib.blb"

    lib = library.Library(util.bytestring_path(lib_db))
    lib.directory = util.bytestring_path(lib_dir)

    lib.path_formats = [
        ("default", helpers.fmt_path("$artist", "$album", "$title")),
        ("singleton:true", helpers.fmt_path("singletons", "$title")),
        ("comp:true", helpers.fmt_path("compilations", "$album", "$title")),
    ]

    yield lib

    lib._close()


@pytest.fixture
def import_dir(tmp_path: Path) -> Path:
    """Return the import source directory path."""
    return tmp_path / "testsrc_dir"


# ---------------------------------------------------------------------------
# Plugin lifecycle
# ---------------------------------------------------------------------------


@pytest.fixture
def beets_plugin_lifecycle() -> Generator[None]:
    """Ensure plugins are cleaned up after each test."""
    yield
    _unload_plugins()
    _teardown_plugin_state()


# ---------------------------------------------------------------------------
# Main entry-point fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def beets_plugin_env(
    tmp_path: Path,
    beets_lib: library.Library,
    lib_dir: Path,
    import_dir: Path,
    _beets_io: DummyIO,
    _beets_plugin_lifecycle: None,
) -> BeetsPluginFixture:
    """The primary fixture for beets plugin tests.

    Usage::

        def test_something(beets_plugin_env: BeetsPluginFixture) -> None:
            beets_plugin_env.create_flat_import_dir()
            beets_plugin_env.setup_import_session(autotag=False)
            config["filetote"]["extensions"] = ".file"
            beets_plugin_env.run_cli_command("import")
            beets_plugin_env.assert_in_lib_dir(
                "Tag Artist/Tag Album/artifact.file"
            )
    """
    return BeetsPluginFixture(
        tmp_path=tmp_path,
        lib=beets_lib,
        lib_dir=lib_dir,
        import_dir=import_dir,
    )
