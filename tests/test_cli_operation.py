"""Tests CLI operations supersede config for the beets-filetote plugin."""

from typing import TYPE_CHECKING

from beets import config

from tests.helper import FiletoteTestCase

if TYPE_CHECKING:
    from pathlib import Path


class FiletoteCLIOperation(FiletoteTestCase):
    """Tests to check handling of the operation (copy, move, etc.) can be
    overridden by the CLI.
    """

    def setUp(self, _other_plugins: list[str] | None = None) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._set_import_dir()
        self.album_path: Path = self.import_dir / "the_album"
        self.album_path.mkdir(parents=True, exist_ok=True)

        self._base_file_count: int = 0

        config["filetote"]["extensions"] = ".file"

    def test_do_nothing_when_not_copying_or_moving(self) -> None:
        """Check that plugin leaves everything alone when not
        copying (-C command line option) and not moving.
        """
        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

        self._base_file_count = self._media_count + self._pairs_count

        config["import"]["copy"] = False
        config["import"]["move"] = False

        self._run_cli_command("import")

        self.assert_number_of_files_in_dir(self._base_file_count + 4, self.album_path)

        self.assert_in_import_dir("the_album/artifact.file")
        self.assert_in_import_dir("the_album/artifact2.file")
        self.assert_in_import_dir("the_album/artifact.nfo")
        self.assert_in_import_dir("the_album/artifact.lrc")

    def test_import_config_copy_false_import_on_copy(self) -> None:
        """Tests that when config does not have an operation set, that
        providing it as `--copy` in the CLI correctly overrides.
        """
        self._setup_import_session(copy=False, autotag=False)

        self.create_file(self.album_path / "\xe4rtifact.file")
        medium = self.create_medium(self.album_path / "track_1.mp3")
        self.import_media = [medium]

        self._run_cli_command("import", operation_option="copy")

        self.assert_in_import_dir("the_album/\xe4rtifact.file")

        self.assert_in_lib_dir("Tag Artist/Tag Album/\xe4rtifact.file")

    def test_import_config_copy_false_import_on_move(self) -> None:
        """Tests that when config does not have an operation set, that
        providing it as `--move` in the CLI correctly overrides.
        """
        self._setup_import_session(copy=False, autotag=False)

        self.create_file(self.album_path / "\xe4rtifact.file")
        medium = self.create_medium(self.album_path / "track_1.mp3")
        self.import_media = [medium]

        self._run_cli_command("import", operation_option="move")

        self.assert_not_in_import_dir("the_album/\xe4rtifact.file")

        self.assert_in_lib_dir("Tag Artist/Tag Album/\xe4rtifact.file")

    def test_import_config_copy_true_import_on_move(self) -> None:
        """Tests that when config operation is set to `copy`, that providing
        `--move` in the CLI correctly overrides.
        """
        self._setup_import_session(copy=True, autotag=False)

        self.create_file(self.album_path / "\xe4rtifact.file")
        medium = self.create_medium(self.album_path / "track_1.mp3")
        self.import_media = [medium]

        self._run_cli_command("import", operation_option="move")

        self.assert_not_in_import_dir("the_album/\xe4rtifact.file")

        self.assert_in_lib_dir("Tag Artist/Tag Album/\xe4rtifact.file")

    def test_import_config_move_true_import_on_copy(self) -> None:
        """Tests that when config operation is set to `move`, that providing
        `--copy` in the CLI correctly overrides.
        """
        self._setup_import_session(move=True, autotag=False)

        self.create_file(self.album_path / "\xe4rtifact.file")
        medium = self.create_medium(self.album_path / "track_1.mp3")
        self.import_media = [medium]

        self._run_cli_command("import", operation_option="copy")

        self.assert_in_import_dir("the_album/\xe4rtifact.file")

        self.assert_in_lib_dir("Tag Artist/Tag Album/\xe4rtifact.file")

    def test_move_on_move_command(self) -> None:
        """Check that plugin detects the correct operation for the "move" (or "mv")
        command, which is MOVE by default.
        """
        self._create_flat_import_dir()

        self._setup_import_session(move=True, autotag=False)

        self.lib.path_formats = [
            ("default", self.fmt_path("Old Lib Artist", "$album", "$title")),
        ]

        self._run_cli_command("import")

        self.lib.path_formats = [
            ("default", self.fmt_path("$artist", "$album", "$title")),
        ]

        self._run_cli_command("move", query="artist:'Tag Artist'")

        self.assert_not_in_lib_dir("Old Lib Artist/Tag Album/artifact.file")

        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")

    def test_copy_on_move_command_copy(self) -> None:
        """Check that plugin detects the correct operation for the "move" (or "mv")
        command when "copy" is set. The files should be present in both the original
        and new Library locations.
        """
        self._create_flat_import_dir()

        self._setup_import_session(move=True, autotag=False)

        self.lib.path_formats = [
            ("default", self.fmt_path("Old Lib Artist", "$album", "$title")),
        ]

        self._run_cli_command("import")

        self.lib.path_formats = [
            ("default", self.fmt_path("$artist", "$album", "$title")),
        ]

        self._run_cli_command("move", query="artist:'Tag Artist'", copy=True)

        self.assert_in_lib_dir("Old Lib Artist/Tag Album/artifact.file")

        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")

    def test_copy_on_move_command_export(self) -> None:
        """Check that plugin detects the correct operation for the "move" (or "mv")
        command when "export" is set. This functionally is the same as "copy" but
        does not alter the Library data.
        """
        self._create_flat_import_dir()

        self._setup_import_session(move=True, autotag=False)

        self.lib.path_formats = [
            ("default", self.fmt_path("Old Lib Artist", "$album", "$title")),
        ]

        self._run_cli_command("import")

        self.lib.path_formats = [
            ("default", self.fmt_path("$artist", "$album", "$title")),
        ]

        self._run_cli_command("move", query="artist:'Tag Artist'", export=True)

        self.assert_in_lib_dir("Old Lib Artist/Tag Album/artifact.file")

        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")

    def test_move_on_modify_command(self) -> None:
        """Check that plugin detects the correct operation for the "move" (or "mv")
        command, which is MOVE by default.
        """
        self._create_flat_import_dir()

        self._setup_import_session(move=True, autotag=False)

        self.lib.path_formats = [
            ("default", self.fmt_path("Old Lib Artist", "$album", "$title")),
        ]

        self._run_cli_command("import")

        self.lib.path_formats = [
            ("default", self.fmt_path("$artist", "$album", "$title")),
        ]

        self._run_cli_command(
            "modify", query="artist:'Tag Artist'", mods={"artist": "Tag Artist New"}
        )

        self.assert_not_in_lib_dir("Old Lib Artist/Tag Album/artifact.file")

        self.assert_in_lib_dir("Tag Artist New/Tag Album/artifact.file")

    def test_move_on_update_move_command(self) -> None:
        """Check that plugin detects the correct operation for the "update"
        command, which will MOVE by default.
        """
        self._create_flat_import_dir()

        self._setup_import_session(move=True, autotag=False)

        self._run_cli_command("import")

        self.update_medium(
            path=(self.lib_dir / "Tag Artist" / "Tag Album" / "Tag Title 1.mp3"),
            meta_updates={"artist": "New Artist Updated"},
        )

        self._run_cli_command(
            "update", query="artist:'Tag Artist'", fields=["artist"], move=True
        )

        self.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.file")

        self.assert_in_lib_dir("New Artist Updated/Tag Album/artifact.file")

    def test_pairs_on_update_move_command(self) -> None:
        """Check that plugin handles "pairs" for the "update"
        command, which will MOVE by default.
        """
        self._create_flat_import_dir()

        self._setup_import_session(move=True, autotag=False)

        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"] = {
            "enabled": True,
            "pairing_only": True,
            "extensions": ".lrc",
        }

        config["paths"]["paired_ext:.lrc"] = "$albumpath/$medianame_new"

        self.lib.path_formats = [
            (
                "default",
                self.fmt_path(
                    "$artist", "$album", "$album - $track - $artist - $title"
                ),
            ),
        ]

        self._run_cli_command("import")

        self.update_medium(
            path=self.lib_dir
            / "Tag Artist"
            / "Tag Album"
            / "Tag Album - 01 - Tag Artist - Tag Title 1.mp3",
            meta_updates={"artist": "New Artist Updated"},
        )

        self._run_cli_command(
            "update", query="artist:'Tag Artist'", fields=["artist"], move=True
        )

        self.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.file")

        self.assert_in_lib_dir(
            "New Artist Updated/Tag Album/Tag Album - 01 - New Artist Updated - "
            "Tag Title 1.lrc"
        )
