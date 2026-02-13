"""Tests pruning for the beets-filetote plugin."""

import logging

from typing import TYPE_CHECKING

from beets import config

from tests.helper import FiletoteTestCase

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger("beets")


class FiletotePruningyTest(FiletoteTestCase):
    """Tests to check that Filetote correctly "prunes" directories when
    it moves artifact files.
    """

    def setUp(self, _other_plugins: list[str] | None = None) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._create_flat_import_dir()

        self.album_path: Path = self.import_dir / "the_album"

        self._setup_import_session(autotag=False, move=True)

    def test_prune_import_directory_when_emptied(self) -> None:
        """Check that plugin does not interfere with normal
        pruning of emptied import directories.
        """
        config["filetote"]["extensions"] = ".*"

        self._run_cli_command("import")

        self.assert_import_dir_exists()
        self.assert_not_in_import_dir("the_album")

    def test_prune_import_subdirectory_only_not_above(self) -> None:
        """Check that plugin only prunes nested folder when specified."""
        self._setup_import_session(
            autotag=False,
            import_dir=self.album_path,
            move=True,
        )
        config["filetote"]["extensions"] = ".*"
        self._run_cli_command("import")

        self.assert_import_dir_exists(self.import_dir)
        self.assert_not_in_import_dir("the_album")

    def test_prunes_empty_artifact_subdirectory_on_move(self) -> None:
        """Tests that when an artifact is moved from a subdirectory within an album,
        the empty subdirectory is correctly pruned.
        """
        artwork_dir_path: Path = self.album_path / "Artwork"

        self.create_file(artwork_dir_path / "background.jpg")

        config["filetote"]["patterns"] = {"artwork": ["[aA]rtwork/"]}
        config["filetote"]["extensions"] = ".*"
        config["filetote"]["paths"] = {
            "pattern:artwork": self.fmt_path("$albumpath", "art", "$old_filename")
        }
        config["import"]["move"] = True

        self._run_cli_command("import")

        self.assert_in_lib_dir("Tag Artist/Tag Album/art/background.jpg")

        self.assert_not_in_import_dir("the_album/Artwork/background.jpg")

        self.assert_not_in_import_dir("the_album/Artwork")
        self.assert_not_in_import_dir("the_album")

    def test_prune_import_expands_user_import_path(self) -> None:
        """Check that plugin prunes and converts/expands the user parts of path if
        present.
        """
        self._setup_import_session(
            autotag=False,
            import_dir=self.album_path,
            move=True,
        )
        config["filetote"]["extensions"] = ".*"
        self._run_cli_command("import")

        self.assert_import_dir_exists(self.import_dir)
        self.assert_not_in_import_dir("the_album")

    def test_prune_reimport_move(self) -> None:
        """Check that plugin prunes to the root of the library when reimporting
        from library.

        Setup subsequent import directory of the following structure:

            testlib_dir/
                Tag Artist/
                    Tag Album/
                        Tag Title 1.mp3
                        Tag Title 2.mp3
                        Tag Title 3.mp3
                        artifact.file
                        artifact2.file
        """
        config["filetote"]["extensions"] = ".file"

        log.debug("--- initial import")
        self._run_cli_command("import")

        self.lib.path_formats[0] = (
            "default",
            self.fmt_path("1$artist", "$album", "$title"),
        )
        self._setup_import_session(autotag=False, import_dir=self.lib_dir, move=True)

        log.debug("--- second import")

        self._run_cli_command("import")

        self.assert_not_in_lib_dir("Tag Artist/Tag Album")
        self.assert_not_in_lib_dir("Tag Artist")
        self.assert_in_lib_dir("1Tag Artist/Tag Album/artifact.file")

    def test_prune_reimport_copy(self) -> None:
        """Ensure directories are pruned when reimporting with 'copy'. The
        operation gets changed to `move` when the media file is already in the
        library (hence, reimport).

        Setup subsequent import directory of the following structure:

            testlib_dir/
                Tag Artist/
                    Tag Album/
                        Tag Title 1.mp3
                        Tag Title 2.mp3
                        Tag Title 3.mp3
                        artifact.file
                        artifact2.file
        """
        config["filetote"]["extensions"] = ".file"

        log.debug("--- initial import")
        self._run_cli_command("import")

        self.lib.path_formats[0] = (
            "default",
            self.fmt_path("1$artist", "$album", "$title"),
        )
        self._setup_import_session(autotag=False, import_dir=self.lib_dir, copy=True)

        log.debug("--- second import")

        self._run_cli_command("import")

        self.assert_not_in_lib_dir("Tag Artist/Tag Album")
        self.assert_not_in_lib_dir("Tag Artist")
        self.assert_in_lib_dir("1Tag Artist/Tag Album/artifact.file")

    def test_prune_reimport_query(self) -> None:
        """Check that plugin prunes to the root of the library when reimporting
        from library using `import` with a query.

        Setup subsequent import directory of the following structure:

            testlib_dir/
                New Tag Artist/
                    Tag Album/
                        Tag Title 1.mp3
                        Tag Title 2.mp3
                        Tag Title 3.mp3
                        artifact.file
                        artifact2.file
        """
        config["filetote"]["extensions"] = ".file"

        log.debug("--- initial import")
        self._run_cli_command("import")

        self.lib.path_formats = [
            ("default", self.fmt_path("New Tag Artist", "$album", "$title")),
        ]
        self._setup_import_session(query="artist", autotag=False, move=True)

        log.debug("--- second import")
        self._run_cli_command("import")

        self.assert_not_in_lib_dir("Tag Artist/Tag Album")
        self.assert_not_in_lib_dir("Tag Artist")
        self.assert_in_lib_dir("New Tag Artist/Tag Album/artifact.file")

    def test_prune_move_query(self) -> None:
        """Check that plugin prunes any remaining empty album folders when using
        the  `move` with a query.

        Setup subsequent import directory of the following structure:

            testlib_dir/
                New Tag Artist/
                    Tag Album/
                        Tag Title 1.mp3
                        Tag Title 2.mp3
                        Tag Title 3.mp3
                        artifact.file
                        artifact2.file
        """
        config["filetote"]["extensions"] = ".file"

        log.debug("--- initial import")
        self._run_cli_command("import")

        self.lib.path_formats = [
            ("default", self.fmt_path("New Tag Artist", "$album", "$title")),
        ]

        log.debug("--- run mover")
        self._run_cli_command("move", query="artist:'Tag Artist'")

        self.assert_not_in_lib_dir("Tag Artist/Tag Album")
        self.assert_not_in_lib_dir("Tag Artist")
        self.assert_in_lib_dir("New Tag Artist/Tag Album/artifact.file")

    def test_prune_modify_query(self) -> None:
        """Check that plugin prunes any remaining empty album folders when using
        the  `modify` with a query.

        Setup subsequent import directory of the following structure:

            testlib_dir/
                New Tag Artist/
                    Tag Album/
                        Tag Title 1.mp3
                        Tag Title 2.mp3
                        Tag Title 3.mp3
                        artifact.file
                        artifact2.file
        """
        config["filetote"]["extensions"] = ".file"

        log.debug("--- initial import")
        self._run_cli_command("import")

        self.lib.path_formats = [
            ("default", self.fmt_path("$artist", "$album", "$title")),
        ]

        log.debug("--- run modify")
        self._run_cli_command(
            "modify", query="artist:'Tag Artist'", mods={"artist": "New Tag Artist"}
        )

        self.assert_not_in_lib_dir("Tag Artist/Tag Album")
        self.assert_not_in_lib_dir("Tag Artist")
        self.assert_in_lib_dir("New Tag Artist/Tag Album/artifact.file")

    def test_prunes_multidisc_nested(self) -> None:
        """Ensures that multidisc nested directories are pruned correctly on move."""
        self._create_nested_import_dir()
        self._setup_import_session(autotag=False, move=True)

        config["filetote"]["extensions"] = ".*"

        self._run_cli_command("import")

        self.assert_not_in_import_dir("the_album/disc1")
        self.assert_not_in_import_dir("the_album/disc2")
        self.assert_not_in_import_dir("the_album")
