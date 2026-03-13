"""Tests pruning of single-disc imports for the beets-filetote plugin."""

from typing import TYPE_CHECKING

import pytest

from tests.pytest_beets_plugin.fixtures import BeetsEnvFactory

if TYPE_CHECKING:
    from pathlib import Path


class TestPruning:
    """Tests to check that Filetote correctly "prunes" directories when
    it moves artifact files.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, beets_flat_env: BeetsEnvFactory) -> None:
        """Provides shared setup for tests."""
        self.env = beets_flat_env(move=True)

    def test_prune_import_directory_when_emptied(self) -> None:
        """Check that plugin does not interfere with normal
        pruning of emptied import directories.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".*"

        env.run_cli_command("import")

        env.assert_import_dir_exists()
        env.assert_not_in_import_dir("the_album")

    def test_prune_import_subdirectory_only_not_above(self) -> None:
        """Check that plugin only prunes nested folder when specified."""
        env = self.env
        album_path = env.import_dir / "the_album"

        env.setup_import_session(
            autotag=False,
            import_dir=album_path,
            move=True,
        )
        env.config["filetote"]["extensions"] = ".*"

        env.run_cli_command("import")

        env.assert_import_dir_exists(env.import_dir)
        env.assert_not_in_import_dir("the_album")

    def test_prunes_empty_artifact_subdirectory_on_move(self) -> None:
        """Tests that when an artifact is moved from a subdirectory within an album,
        the empty subdirectory is correctly pruned.
        """
        env = self.env
        album_path = env.import_dir / "the_album"
        artwork_dir_path: Path = album_path / "Artwork"

        env.create_file(artwork_dir_path / "background.jpg")

        env.config["filetote"]["patterns"] = {"artwork": ["[aA]rtwork/"]}
        env.config["filetote"]["extensions"] = ".*"
        env.config["filetote"]["paths"] = {
            "pattern:artwork": env.fmt_path("$albumpath", "art", "$old_filename")
        }

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/art/background.jpg")

        env.assert_not_in_import_dir("the_album/Artwork/background.jpg")
        env.assert_not_in_import_dir("the_album/Artwork")
        env.assert_not_in_import_dir("the_album")

    def test_prune_import_expands_user_import_path(self) -> None:
        """Check that plugin prunes and converts/expands the user parts of path if
        present.
        """
        env = self.env
        album_path = env.import_dir / "the_album"

        env.setup_import_session(
            autotag=False,
            import_dir=album_path,
            move=True,
        )
        env.config["filetote"]["extensions"] = ".*"

        env.run_cli_command("import")

        env.assert_import_dir_exists(env.import_dir)
        env.assert_not_in_import_dir("the_album")

    def test_prune_reimport_move(self) -> None:
        """Check that plugin prunes to the root of the library when reimporting
        from library.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".file"

        env.log.debug("--- initial import")
        env.run_cli_command("import")

        env.lib.path_formats[0] = (
            "default",
            env.fmt_path("1$artist", "$album", "$title"),
        )
        env.setup_import_session(autotag=False, import_dir=env.lib_dir, move=True)

        env.log.debug("--- second import")
        env.run_cli_command("import")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album")
        env.assert_not_in_lib_dir("Tag Artist")
        env.assert_in_lib_dir("1Tag Artist/Tag Album/artifact.file")

    def test_prune_reimport_copy(self) -> None:
        """Ensure directories are pruned when reimporting with 'copy'. The
        operation gets changed to `move` when the media file is already in the
        library (hence, reimport).
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".file"

        env.log.debug("--- initial import")
        env.run_cli_command("import")

        env.lib.path_formats[0] = (
            "default",
            env.fmt_path("1$artist", "$album", "$title"),
        )
        env.setup_import_session(autotag=False, import_dir=env.lib_dir, copy=True)

        env.log.debug("--- second import")
        env.run_cli_command("import")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album")
        env.assert_not_in_lib_dir("Tag Artist")
        env.assert_in_lib_dir("1Tag Artist/Tag Album/artifact.file")

    def test_prune_reimport_query(self) -> None:
        """Check that plugin prunes to the root of the library when reimporting
        from library using `import` with a query.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".file"

        env.log.debug("--- initial import")
        env.run_cli_command("import")

        env.lib.path_formats = [
            ("default", env.fmt_path("New Tag Artist", "$album", "$title")),
        ]
        env.setup_import_session(query="artist", autotag=False, move=True)

        env.log.debug("--- second import")
        env.run_cli_command("import")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album")
        env.assert_not_in_lib_dir("Tag Artist")
        env.assert_in_lib_dir("New Tag Artist/Tag Album/artifact.file")

    def test_prune_move_query(self) -> None:
        """Check that plugin prunes any remaining empty album folders when using
        the `move` with a query.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".file"

        env.log.debug("--- initial import")
        env.run_cli_command("import")

        env.lib.path_formats = [
            ("default", env.fmt_path("New Tag Artist", "$album", "$title")),
        ]

        env.log.debug("--- run mover")
        env.run_cli_command("move", query="artist:'Tag Artist'")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album")
        env.assert_not_in_lib_dir("Tag Artist")
        env.assert_in_lib_dir("New Tag Artist/Tag Album/artifact.file")

    def test_prune_modify_query(self) -> None:
        """Check that plugin prunes any remaining empty album folders when using
        the `modify` with a query.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".file"

        env.log.debug("--- initial import")
        env.run_cli_command("import")

        env.lib.path_formats = [
            ("default", env.fmt_path("$artist", "$album", "$title")),
        ]

        env.log.debug("--- run modify")
        env.run_cli_command(
            "modify",
            query="artist:'Tag Artist'",
            mods={"artist": "New Tag Artist"},
        )

        env.assert_not_in_lib_dir("Tag Artist/Tag Album")
        env.assert_not_in_lib_dir("Tag Artist")
        env.assert_in_lib_dir("New Tag Artist/Tag Album/artifact.file")
