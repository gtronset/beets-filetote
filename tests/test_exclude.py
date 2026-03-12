"""Tests to ensure the `exclude` settings properly excludes files in the beets-filetote
plugin.
"""

import pytest

from tests.pytest_beets_plugin import BeetsPluginFixture

_EXCLUDE_DEPRECATION_MSG = (
    "filetote: Deprecation warning: The `exclude` setting should now use"
    " the explicit settings of `filenames`, `extensions`, and/or"
    " `patterns`. See the `exclude` documentation for more details:"
    " https://github.com/gtronset/beets-filetote#excluding-files"
)


class TestExclude:
    """Tests to ensure the `exclude` settings properly excludes files in the
    beets-filetote plugin.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, beets_plugin_env: BeetsPluginFixture) -> None:
        """Provides shared setup for tests."""
        self.env = beets_plugin_env
        self.env.create_flat_import_dir()
        self.env.setup_import_session(move=True, autotag=False)

    def test_exclude_rule_overrides_inclusion_rules(self) -> None:
        """Tests to ensure the `exclude` config properly excludes files even when
        they would otherwise be included. (Exclude takes precedence over include).
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["exclude"] = {
            "extensions": [".lrc"],
        }

        album_path = env.import_dir / "the_album"

        env.create_file(album_path / "not_to_be_moved.lrc")

        env.run_cli_command("import")

        env.assert_in_import_dir("the_album/not_to_be_moved.lrc")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/not_to_be_moved.lrc")

    def test_exclude_strseq_of_filenames_by_string(self) -> None:
        """Tests to ensure the `exclude` config registers as a strseq (string
        sequence) of filenames.
        """
        env = self.env
        env.config["filetote"]["extensions"] = ".file .lrc"
        env.config["filetote"]["exclude"] = "not_to_be_moved.file not_to_be_moved.lrc"
        env.config["paths"]["ext:file"] = "$albumpath/$old_filename"

        album_path = env.import_dir / "the_album"

        env.create_file(album_path / "not_to_be_moved.file")
        env.create_file(album_path / "not_to_be_moved.lrc")

        with env.capture_log("beets.filetote") as logs:
            env.run_cli_command("import")

        env.assert_in_import_dir("the_album/not_to_be_moved.file")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/not_to_be_moved.file")

        env.assert_in_import_dir("the_album/not_to_be_moved.lrc")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/not_to_be_moved.lrc")

        # Ensure the deprecation warning is present
        assert logs == [_EXCLUDE_DEPRECATION_MSG]

    def test_exclude_strseq_of_filenames_by_list(self) -> None:
        """Tests to ensure the `exclude` config registers as a strseq (string
        sequence) of filenames.
        """
        env = self.env
        env.config["filetote"]["extensions"] = ".file .lrc"
        env.config["filetote"]["exclude"] = [
            "not_to_be_moved.file",
            "not_to_be_moved.lrc",
        ]
        env.config["paths"]["ext:file"] = "$albumpath/$old_filename"

        album_path = env.import_dir / "the_album"

        env.create_file(album_path / "not_to_be_moved.file")
        env.create_file(album_path / "not_to_be_moved.lrc")

        with env.capture_log("beets.filetote") as logs:
            env.run_cli_command("import")

        env.assert_in_import_dir("the_album/not_to_be_moved.file")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/not_to_be_moved.file")

        env.assert_in_import_dir("the_album/not_to_be_moved.lrc")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/not_to_be_moved.lrc")

        # Ensure the deprecation warning is present
        assert logs == [_EXCLUDE_DEPRECATION_MSG]

    def test_exclude_dict_with_filenames_extensions(self) -> None:
        """Tests to ensure the `exclude` config registers dictionary of `filenames`
        and/or `extensions`.
        """
        env = self.env
        env.config["filetote"]["extensions"] = ".*"

        env.config["filetote"]["exclude"] = {
            "filenames": ["not_to_be_moved.file"],
            "extensions": [".lrc"],
        }

        album_path = env.import_dir / "the_album"

        env.create_file(album_path / "not_to_be_moved.file")
        env.create_file(album_path / "not_to_be_moved.lrc")

        env.run_cli_command("import")

        env.assert_in_import_dir("the_album/not_to_be_moved.file")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/not_to_be_moved.file")

        env.assert_in_import_dir("the_album/not_to_be_moved.lrc")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/not_to_be_moved.lrc")

    def test_exclude_dict_with_patterns(self) -> None:
        """Tests to ensure the `exclude` config and works with and patterns."""
        env = self.env
        env.config["filetote"]["extensions"] = ".*"

        env.config["filetote"]["exclude"]["patterns"] = {
            "file-pattern": ["[aA]rtifact.*"],
            "nfo-pattern": ["*.lrc"],
        }

        album_path = env.import_dir / "the_album"

        env.create_file(album_path / "to_be_moved.file")
        env.create_file(album_path / "not_to_be_moved.lrc")

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/to_be_moved.file")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/not_to_be_moved.lrc")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")
