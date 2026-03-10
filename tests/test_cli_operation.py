"""Tests CLI operations supersede config for the beets-filetote plugin."""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.pytest_beets_plugin.plugin_fixture import BeetsPluginFixture


class TestFiletoteCLIOperation:
    """Tests to check handling of the operation (copy, move, etc.) can be
    overridden by the CLI.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, beets_plugin_env: "BeetsPluginFixture") -> None:
        """All tests in this class load the audible stub plugin."""
        self.env = beets_plugin_env
        self.env.config["filetote"]["extensions"] = ".file"

    def test_do_nothing_when_not_copying_or_moving(self) -> None:
        """Check that plugin leaves everything alone when not
        copying (-C command line option) and not moving.
        """
        env = self.env

        env.create_flat_import_dir()
        env.setup_import_session(autotag=False)

        base_file_count = env.media_count + env.pairs_count

        env.config["import"]["copy"] = False
        env.config["import"]["move"] = False

        env.run_cli_command("import")

        album_path = env.import_dir / "the_album"
        env.assert_number_of_files_in_dir(base_file_count + 4, album_path)

        env.assert_in_import_dir("the_album/artifact.file")
        env.assert_in_import_dir("the_album/artifact2.file")
        env.assert_in_import_dir("the_album/artifact.nfo")
        env.assert_in_import_dir("the_album/artifact.lrc")

    def test_import_config_copy_false_import_on_copy(self) -> None:
        """Tests that when config does not have an operation set, that
        providing it as `--copy` in the CLI correctly overrides.
        """
        env = self.env

        env.create_simple_import_dir(artifacts=["artifact.file"])
        env.setup_import_session(copy=False, autotag=False)

        env.run_cli_command("import", operation_option="copy")

        env.assert_in_import_dir("the_album/artifact.file")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")

    def test_import_config_copy_false_import_on_move(self) -> None:
        """Tests that when config does not have an operation set, that
        providing it as `--move` in the CLI correctly overrides.
        """
        env = self.env

        env.create_simple_import_dir(artifacts=["artifact.file"])
        env.setup_import_session(copy=False, autotag=False)

        env.run_cli_command("import", operation_option="move")

        env.assert_not_in_import_dir("the_album/artifact.file")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")

    def test_import_config_copy_true_import_on_move(self) -> None:
        """Tests that when config operation is set to `copy`, that providing
        `--move` in the CLI correctly overrides.
        """
        env = self.env

        env.create_simple_import_dir(artifacts=["artifact.file"])
        env.setup_import_session(copy=True, autotag=False)

        env.run_cli_command("import", operation_option="move")

        env.assert_not_in_import_dir("the_album/artifact.file")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")

    def test_import_config_move_true_import_on_copy(self) -> None:
        """Tests that when config operation is set to `move`, that providing
        `--copy` in the CLI correctly overrides.
        """
        env = self.env

        env.create_simple_import_dir(artifacts=["artifact.file"])
        env.setup_import_session(copy=False, move=True, autotag=False)

        env.run_cli_command("import", operation_option="copy")

        env.assert_in_import_dir("the_album/artifact.file")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")

    def test_move_on_move_command(self) -> None:
        """Check that plugin detects the correct operation for the "move" (or "mv")
        command, which is MOVE by default.
        """
        env = self.env

        env.create_flat_import_dir()
        env.setup_import_session(move=True, autotag=False)

        env.lib.path_formats = [
            ("default", env.fmt_path("Old Lib Artist", "$album", "$title")),
        ]

        env.run_cli_command("import")

        env.lib.path_formats = [
            ("default", env.fmt_path("$artist", "$album", "$title")),
        ]

        env.run_cli_command("move", query="artist:'Tag Artist'")

        env.assert_not_in_lib_dir("Old Lib Artist/Tag Album/artifact.file")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")

    def test_copy_on_move_command_copy(self) -> None:
        """Check that plugin detects the correct operation for the "move" (or "mv")
        command when "copy" is set. The files should be present in both the original
        and new Library locations.
        """
        env = self.env

        env.create_flat_import_dir()
        env.setup_import_session(move=True, autotag=False)

        env.lib.path_formats = [
            ("default", env.fmt_path("Old Lib Artist", "$album", "$title")),
        ]

        env.run_cli_command("import")

        env.lib.path_formats = [
            ("default", env.fmt_path("$artist", "$album", "$title")),
        ]

        env.run_cli_command("move", query="artist:'Tag Artist'", copy=True)

        env.assert_in_lib_dir("Old Lib Artist/Tag Album/artifact.file")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")

    def test_copy_on_move_command_export(self) -> None:
        """Check that plugin detects the correct operation for the "move" (or "mv")
        command when "export" is set. This functionally is the same as "copy" but
        does not alter the Library data.
        """
        env = self.env

        env.create_flat_import_dir()
        env.setup_import_session(move=True, autotag=False)

        env.lib.path_formats = [
            ("default", env.fmt_path("Old Lib Artist", "$album", "$title")),
        ]

        env.run_cli_command("import")

        env.lib.path_formats = [
            ("default", env.fmt_path("$artist", "$album", "$title")),
        ]

        env.run_cli_command("move", query="artist:'Tag Artist'", export=True)

        env.assert_in_lib_dir("Old Lib Artist/Tag Album/artifact.file")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")

    def test_move_on_modify_command(self) -> None:
        """Check that plugin detects the correct operation for the "move" (or "mv")
        command, which is MOVE by default.
        """
        env = self.env

        env.create_flat_import_dir()
        env.setup_import_session(move=True, autotag=False)

        env.lib.path_formats = [
            ("default", env.fmt_path("Old Lib Artist", "$album", "$title")),
        ]

        env.run_cli_command("import")

        env.lib.path_formats = [
            ("default", env.fmt_path("$artist", "$album", "$title")),
        ]

        env.run_cli_command(
            "modify", query="artist:'Tag Artist'", mods={"artist": "Tag Artist New"}
        )

        env.assert_not_in_lib_dir("Old Lib Artist/Tag Album/artifact.file")

        env.assert_in_lib_dir("Tag Artist New/Tag Album/artifact.file")

    def test_move_on_update_move_command(self) -> None:
        """Check that plugin detects the correct operation for the "update"
        command, which will MOVE by default.
        """
        env = self.env

        env.create_flat_import_dir()
        env.setup_import_session(move=True, autotag=False)

        env.run_cli_command("import")

        env.update_medium(
            path=(env.lib_dir / "Tag Artist" / "Tag Album" / "Tag Title 1.mp3"),
            meta_updates={"artist": "New Artist Updated"},
        )

        env.run_cli_command(
            "update", query="artist:'Tag Artist'", fields=["artist"], move=True
        )

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.file")

        env.assert_in_lib_dir("New Artist Updated/Tag Album/artifact.file")

    def test_pairs_on_update_move_command(self) -> None:
        """Check that plugin handles "pairs" for the "update"
        command, which will MOVE by default.
        """
        env = self.env

        env.create_flat_import_dir()
        env.setup_import_session(move=True, autotag=False)

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"] = {
            "enabled": True,
            "pairing_only": True,
            "extensions": ".lrc",
        }

        env.config["paths"]["paired_ext:.lrc"] = "$albumpath/$medianame_new"

        env.lib.path_formats = [
            (
                "default",
                env.fmt_path("$artist", "$album", "$album - $track - $artist - $title"),
            ),
        ]

        env.run_cli_command("import")

        env.update_medium(
            path=env.lib_dir
            / "Tag Artist"
            / "Tag Album"
            / "Tag Album - 01 - Tag Artist - Tag Title 1.mp3",
            meta_updates={"artist": "New Artist Updated"},
        )

        env.run_cli_command(
            "update", query="artist:'Tag Artist'", fields=["artist"], move=True
        )

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.file")

        env.assert_in_lib_dir(
            "New Artist Updated/Tag Album/Tag Album - 01 - New Artist Updated - "
            "Tag Title 1.lrc"
        )
