"""Pytest fixtures for beets plugin tests."""

# ruff: noqa: SLF001

import logging

from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any

import pytest

from beets import config, library, util

from ._io import DummyIO
from .media import MediaSetup
from .plugin_fixture import BeetsPluginFixture
from .plugin_lifecycle import _clear_plugin_state, _deactivate_plugins
from .utils import BeetsTestUtils

log = logging.getLogger("beets")

BeetsEnvFactory = Callable[..., BeetsPluginFixture]


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

    Properly closes the library on teardown.
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

    - `_beets_config` — config isolation (pulled in via `_beets_lib`)
    - `_beets_lib` — temporary library + database (with teardown)
    - `_beets_io` — stdin/stdout capture
    - `_beets_plugin_lifecycle` — plugin teardown on exit
    """
    lib, lib_dir = _beets_lib
    import_dir = tmp_path / "testsrc_dir"

    return BeetsPluginFixture(
        tmp_path=tmp_path,
        lib=lib,
        lib_dir=lib_dir,
        import_dir=import_dir,
    )


# ---------------------------------------------------------------------------
# Convenience fixtures — common setups
# ---------------------------------------------------------------------------


@pytest.fixture
def beets_flat_env(
    beets_plugin_env: BeetsPluginFixture,
) -> BeetsEnvFactory:
    """Factory fixture for flat (single-disc) import environments.

    Returns a callable that creates the import dir and configures the session. All
    `setup_import_session` kwargs are forwarded:

        def test_copy(self, beets_flat_env):
            env = beets_flat_env()  # defaults: autotag=False, copy=True

        def test_move(self, beets_flat_env):
            env = beets_flat_env(move=True)

        def test_custom_media(self, beets_flat_env):
            env = beets_flat_env(
                media_files=[MediaSetup(file_type="wav", count=2)],
                move=True,
                pair_subfolders=True,
            )
    """

    def _factory(
        media_files: list[MediaSetup] | None = None,
        pair_subfolders: bool = False,
        **session_kwargs: Any,
    ) -> BeetsPluginFixture:
        session_kwargs.setdefault("autotag", False)

        beets_plugin_env.create_flat_import_dir(
            media_files=media_files,
            pair_subfolders=pair_subfolders,
        )
        beets_plugin_env.setup_import_session(**session_kwargs)
        return beets_plugin_env

    return _factory


@pytest.fixture
def beets_nested_env(
    beets_plugin_env: BeetsPluginFixture,
) -> BeetsEnvFactory:
    """Factory fixture for nested (multi-disc) import environments.

    Returns a callable that creates the import dir and configures the session. All
    `setup_import_session` kwargs are forwarded:

        def test_copy(self, beets_nested_env):
            env = beets_nested_env()  # defaults: autotag=False, copy=True

        def test_move(self, beets_nested_env):
            env = beets_nested_env(move=True)

        def test_parent_files(self, beets_nested_env):
            env = beets_nested_env(
                parent_artifacts=["summary.txt", "artwork/poster.jpg"],
                move=True,
            )
    """

    def _factory(
        disc1_media_files: list[MediaSetup] | None = None,
        disc2_media_files: list[MediaSetup] | None = None,
        parent_artifacts: list[str] | None = None,
        **session_kwargs: Any,
    ) -> BeetsPluginFixture:
        session_kwargs.setdefault("autotag", False)

        beets_plugin_env.create_nested_import_dir(
            disc1_media_files=disc1_media_files,
            disc2_media_files=disc2_media_files,
            parent_artifacts=parent_artifacts,
        )
        beets_plugin_env.setup_import_session(**session_kwargs)
        return beets_plugin_env

    return _factory
