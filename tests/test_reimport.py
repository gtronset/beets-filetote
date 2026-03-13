"""Tests reimporting for the beets-filetote plugin."""

import pytest

from tests.pytest_beets_plugin.fixtures import BeetsEnvFactory


class TestReimport:
    """Tests to check that Filetote handles reimports correctly."""

    @pytest.fixture(autouse=True)
    def _setup(self, beets_flat_env: BeetsEnvFactory) -> None:
        """Perform an initial import so each test starts with artifacts in the
        library.

        Library structure after setup::

            testlib_dir/
                Tag Artist/
                    Tag Album/
                        Tag Title 1.mp3
                        Tag Title 2.mp3
                        Tag Title 3.mp3
                        artifact.file
                        artifact2.file
        """
        self.env = beets_flat_env(move=True)

        env = self.env

        env.config["filetote"]["extensions"] = ".file"
        env.config["paths"]["ext:file"] = env.fmt_path("$albumpath", "$old_filename")

        env.log.debug("--- initial import")
        env.run_cli_command("import")

    def test_reimport_artifacts_with_copy(self) -> None:
        """Tests that when reimporting, copying actually results in a move. The
        operation gets changed to `move` when the media file is already in the
        library (hence, reimport).
        """
        env = self.env

        env.lib.path_formats[0] = (
            "default",
            env.fmt_path("1$artist", "$album", "$title"),
        )
        env.setup_import_session(autotag=False, import_dir=env.lib_dir)

        env.log.debug("--- second import")
        env.run_cli_command("import")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("1Tag Artist/Tag Album/artifact.file")

    def test_reimport_artifacts_with_move(self) -> None:
        """Tests that when reimporting, moving works."""
        env = self.env

        env.lib.path_formats[0] = (
            "default",
            env.fmt_path("1$artist", "$album", "$title"),
        )
        env.setup_import_session(autotag=False, import_dir=env.lib_dir, move=True)

        env.log.debug("--- second import")
        env.run_cli_command("import")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("1Tag Artist/Tag Album/artifact.file")

    def test_do_nothing_when_paths_do_not_change_with_copy_import(self) -> None:
        """Tests that when paths are the same (before/after), no action is
        taken for default `copy` action.
        """
        env = self.env

        env.setup_import_session(autotag=False, import_dir=env.lib_dir)

        env.log.debug("--- second import")
        env.run_cli_command("import")

        env.assert_number_of_files_in_dir(5, env.lib_dir / "Tag Artist" / "Tag Album")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")

    def test_do_nothing_when_paths_do_not_change_with_move_import(self) -> None:
        """Tests that when paths are the same (before/after), no action is
        taken for default `move` action.
        """
        env = self.env

        env.setup_import_session(autotag=False, import_dir=env.lib_dir, move=True)

        env.log.debug("--- second import")
        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")

    def test_do_nothing_when_paths_are_identical_with_move_import(self) -> None:
        """Tests that when source and destination paths are identical, Filetote
        should skip processing entirely to avoid unnecessary "artifact already
        exists" warnings.
        """
        env = self.env

        env.setup_import_session(autotag=False, import_dir=env.lib_dir, move=True)

        with env.capture_log("beets.filetote") as logs:
            env.log.debug("--- second import")
            env.run_cli_command("import")

        assert any("Source and destination are the same" in line for line in logs)

        assert not any(
            "Skipping artifact" in line and "already exists" in line for line in logs
        )

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")

    def test_rename_with_copy_reimport(self) -> None:
        """Tests that renaming during `copy` works even when reimporting."""
        env = self.env

        env.config["paths"]["ext:file"] = env.fmt_path("$albumpath", "$artist - $album")
        env.setup_import_session(autotag=False, import_dir=env.lib_dir)

        env.log.debug("--- second import")
        env.run_cli_command("import")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Artist - Tag Album.file")

    def test_rename_with_move_reimport(self) -> None:
        """Tests that renaming during `move` works even when reimporting."""
        env = self.env

        env.config["paths"]["ext:file"] = env.fmt_path("$albumpath", "$artist - $album")
        env.setup_import_session(autotag=False, import_dir=env.lib_dir, move=True)

        env.log.debug("--- second import")
        env.run_cli_command("import")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Artist - Tag Album.file")

    def test_rename_when_paths_do_not_change(self) -> None:
        """This test considers the situation where the path format for a file extension
        is changed and files already in the library are reimported and renamed to
        reflect the change.
        """
        env = self.env

        env.config["paths"]["ext:file"] = env.fmt_path("$albumpath", "$album")
        env.setup_import_session(autotag=False, import_dir=env.lib_dir, move=True)

        env.log.debug("--- second import")
        env.run_cli_command("import")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Album.file")

    def test_multiple_reimport_artifacts_with_move(self) -> None:
        """Tests that multiple reimports work the same as the initial action or
        a single reimport.
        """
        env = self.env

        # --- first reimport
        env.lib.path_formats[0] = (
            "default",
            env.fmt_path("1$artist", "$album", "$title"),
        )
        env.setup_import_session(autotag=False, import_dir=env.lib_dir, move=True)
        env.config["paths"]["ext:file"] = env.fmt_path(
            "$albumpath", "$old_filename - import I"
        )

        env.log.debug("--- first reimport")
        env.run_cli_command("import")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact2.file")
        env.assert_in_lib_dir("1Tag Artist/Tag Album/artifact - import I.file")
        env.assert_in_lib_dir("1Tag Artist/Tag Album/artifact2 - import I.file")

        # --- second reimport
        env.lib.path_formats[0] = (
            "default",
            env.fmt_path("2$artist", "$album", "$title"),
        )
        env.setup_import_session(autotag=False, import_dir=env.lib_dir, move=True)
        env.config["paths"]["ext:file"] = env.fmt_path("$albumpath", "$old_filename I")

        env.log.debug("--- second reimport")
        env.run_cli_command("import")

        env.assert_not_in_lib_dir("1Tag Artist/Tag Album/artifact - import I.file")
        env.assert_not_in_lib_dir("1Tag Artist/Tag Album/artifact2 - import I.file")
        env.assert_in_lib_dir("2Tag Artist/Tag Album/artifact - import I I.file")
        env.assert_in_lib_dir("2Tag Artist/Tag Album/artifact2 - import I I.file")

        # --- third reimport
        env.lib.path_formats[0] = (
            "default",
            env.fmt_path("3$artist", "$album", "$title"),
        )
        env.setup_import_session(autotag=False, import_dir=env.lib_dir, move=True)

        env.log.debug("--- third reimport")
        env.run_cli_command("import")

        env.assert_not_in_lib_dir("2Tag Artist/Tag Album/artifact - import I I.file")
        env.assert_not_in_lib_dir("2Tag Artist/Tag Album/artifact2 - import I I.file")
        env.assert_in_lib_dir("3Tag Artist/Tag Album/artifact - import I I I.file")
        env.assert_in_lib_dir("3Tag Artist/Tag Album/artifact2 - import I I I.file")

    def test_reimport_artifacts_with_query(self) -> None:
        """Tests that when reimporting with a query, artifacts are moved."""
        env = self.env

        env.lib.path_formats = [
            ("default", env.fmt_path("New Tag Artist", "$album", "$title")),
        ]
        env.setup_import_session(query="artist", autotag=False, move=True)

        env.log.debug("--- second import")
        env.run_cli_command("import")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("New Tag Artist/Tag Album/artifact.file")
