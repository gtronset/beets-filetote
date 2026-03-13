"""Tests renaming for the beets-filetote plugin."""

# ruff: noqa: PLR0904

import pytest

from tests.pytest_beets_plugin import BeetsEnvFactory

_WILDCARD_EXT_ERROR = (
    "Error: path query `ext:.*` is not valid. If you are trying to set"
    " a default/fallback, please use `filetote:default` instead."
)


class TestRename:
    """Tests to check that Filetote renames as expected for custom path formats (both
    by extension and filename).
    """

    @pytest.fixture(autouse=True)
    def _setup(self, beets_flat_env: BeetsEnvFactory) -> None:
        """Provides shared setup for tests."""
        self.env = beets_flat_env()

    def test_rename_when_copying(self) -> None:
        """Tests that renaming works when copying."""
        env = self.env

        env.config["filetote"]["extensions"] = ".file"
        env.config["paths"]["ext:file"] = "$albumpath/$artist - $album"

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Artist - Tag Album.file")
        env.assert_in_import_dir("the_album/artifact.file")
        env.assert_in_import_dir("the_album/artifact2.file")

    def test_rename_when_moving(self) -> None:
        """Tests that renaming works when moving."""
        env = self.env

        env.config["filetote"]["extensions"] = ".file"
        env.config["paths"]["ext:file"] = "$albumpath/$artist - $album"
        env.config["import"]["move"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Artist - Tag Album.file")
        env.assert_not_in_import_dir("the_album/artifact.file")

    def test_rename_paired_default(self) -> None:
        """Tests that paired artifacts default to `medianame_new`."""
        env = self.env

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"]["enabled"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 2.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 3.lrc")

    def test_rename_paired_ext(self) -> None:
        """Tests that the value of `medianame_new` populates in renaming."""
        env = self.env

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"]["enabled"] = True
        env.config["paths"]["paired_ext:lrc"] = "$albumpath/$medianame_new Override"

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1 Override.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 2 Override.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 3 Override.lrc")

    def test_rename_paired_ext_does_not_conflict_with_ext(self) -> None:
        """Tests that paired path definitions work alongside `ext` ones."""
        env = self.env

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"]["enabled"] = True
        env.config["paths"]["ext:lrc"] = "$albumpath/1 $old_filename"
        env.config["paths"]["paired_ext:lrc"] = "$albumpath/$medianame_new"

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/1 artifact.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 2.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 3.lrc")

    def test_rename_paired_ext_is_prioritized_over_ext(self) -> None:
        """Tests that paired path definitions supersede `ext` ones when there's a
        collision.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"]["enabled"] = True
        env.config["paths"]["paired_ext:lrc"] = "$albumpath/$medianame_new"
        env.config["paths"]["ext:lrc"] = "$albumpath/1 $old_filename"

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/1 artifact.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 2.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 3.lrc")

    def test_rename_filename_is_prioritized_over_paired_ext(self) -> None:
        """Tests that filename path definitions supersede `paired` ones when there's
        a collision.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"]["enabled"] = True
        env.config["paths"]["paired_ext:lrc"] = "$albumpath/$medianame_new"
        env.config["paths"]["filename:track_1.lrc"] = "$albumpath/1 $old_filename"

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/1 track_1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 2.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 3.lrc")

    def test_rename_period_is_optional_for_ext(self) -> None:
        """Tests that leading periods are optional when defining `ext` paths."""
        env = self.env

        env.config["filetote"]["extensions"] = ".file .nfo"
        env.config["paths"]["ext:file"] = "$albumpath/$artist - $album"
        env.config["paths"]["ext:.nfo"] = "$albumpath/$artist - $album 2"
        env.config["import"]["move"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Artist - Tag Album.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Artist - Tag Album 2.nfo")
        env.assert_not_in_import_dir("the_album/artifact.file")
        env.assert_not_in_import_dir("the_album/artifact.nfo")

    def test_rename_ignores_file_when_name_conflicts(self) -> None:
        """Ensure that if there are multiple files that would rename to the exact same
        name, that only the first is renamed (moved/copied/etc.) but not subsequent ones
        that conflict.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".file"
        env.config["paths"]["ext:file"] = "$albumpath/$artist - $album"
        env.config["import"]["move"] = True

        env.run_cli_command("import")

        # `artifact.file` correctly renames.
        env.assert_not_in_import_dir("the_album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Artist - Tag Album.file")

        # `artifact2.file` will not rename since the destination filename conflicts
        # with `artifact.file`
        env.assert_in_import_dir("the_album/artifact2.file")

    def test_rename_multiple_extensions(self) -> None:
        """Ensure that specifying multiple extensions and definitions properly
        rename.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".file .nfo"
        env.config["paths"]["ext:file"] = "$albumpath/$artist - $album"
        env.config["paths"]["ext:nfo"] = "$albumpath/$artist - $album"
        env.config["import"]["move"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Artist - Tag Album.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Artist - Tag Album.nfo")
        env.assert_not_in_import_dir("the_album/artifact.file")
        env.assert_not_in_import_dir("the_album/artifact.nfo")
        # `artifact2.file` will not rename since the destination filename conflicts
        # with `artifact.file`
        env.assert_in_import_dir("the_album/artifact2.file")

    def test_rename_matching_filename(self) -> None:
        """Ensure that `filename` path definitions rename correctly."""
        env = self.env

        env.config["filetote"]["filenames"] = "artifact.file artifact2.file"
        env.config["paths"]["filename:artifact.file"] = "$albumpath/new-filename"
        env.config["paths"]["filename:artifact2.file"] = (
            "$albumpath/another-new-filename"
        )
        env.config["import"]["move"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/new-filename.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/another-new-filename.file")
        env.assert_not_in_import_dir("the_album/artifact.file")
        env.assert_not_in_import_dir("the_album/artifact2.file")

    def test_rename_prioritizes_filename_over_ext(self) -> None:
        """Tests that filename path definitions supersede `ext` ones when there's
        a collision.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".file"
        env.config["filetote"]["filenames"] = "artifact.file"
        env.config["paths"]["ext:file"] = "$albumpath/$artist - $old_filename"
        env.config["paths"]["filename:artifact.file"] = "$albumpath/new-filename"
        env.config["import"]["move"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/new-filename.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Artist - artifact2.file")

        env.assert_not_in_import_dir("the_album/artifact1.file")
        env.assert_not_in_import_dir("the_album/artifact2.file")

    def test_rename_prioritizes_filename_over_ext_reversed(self) -> None:
        """Ensure the order of path definitions does not affect the priority
        order.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".file"
        env.config["filetote"]["filenames"] = "artifact.file"
        # Order of paths matter here; this is the opposite order as
        # `test_rename_prioritizes_filename_over_ext`
        env.config["paths"]["filename:artifact.file"] = "$albumpath/new-filename"
        env.config["paths"]["ext:file"] = "$albumpath/$artist - $old_filename"
        env.config["import"]["move"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/new-filename.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Artist - artifact2.file")

        env.assert_not_in_import_dir("the_album/artifact1.file")
        env.assert_not_in_import_dir("the_album/artifact2.file")

    def test_rename_multiple_files_prioritizes_filename_over_ext(self) -> None:
        """Tests that multiple filename path definitions still supersede `ext`
        ones when there's collision(s).
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".file"
        env.config["filetote"]["filenames"] = "artifact.file artifact2.file"
        env.config["paths"]["ext:file"] = "$albumpath/$artist - $old_filename"
        env.config["paths"]["filename:artifact.file"] = "$albumpath/new-filename"
        env.config["paths"]["filename:artifact2.file"] = "$albumpath/new-filename2"
        env.config["import"]["move"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/new-filename.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/new-filename2.file")

        env.assert_not_in_import_dir("the_album/artifact1.file")
        env.assert_not_in_import_dir("the_album/artifact2.file")

    def test_rename_path_query_priority(self) -> None:
        """Tests that the path query priority is correctly enforced when multiple
        rules could apply.

        The expected priority is: `filename` > `paired_ext` > `pattern` > `ext`.
        """
        env = self.env
        album_path = env.import_dir / "the_album"

        env.create_file(album_path / "track_1.log")

        env.config["filetote"]["extensions"] = ".log"
        env.config["filetote"]["filenames"] = "track_1.log"
        env.config["filetote"]["pairing"]["enabled"] = True
        env.config["filetote"]["patterns"] = {"logs": ["*.log"]}

        env.config["paths"] = {
            # Lowest priority
            "ext:log": env.fmt_path("$albumpath", "from_ext", "$old_filename"),
            # Mid priority
            "pattern:logs": env.fmt_path("$albumpath", "from_pattern", "$old_filename"),
            # High priority
            "paired_ext:log": env.fmt_path(
                "$albumpath", "from_paired", "$old_filename"
            ),
            # Highest priority
            "filename:track_1.log": env.fmt_path(
                "$albumpath", "from_filename", "$old_filename"
            ),
        }

        env.run_cli_command("import")

        # Assert that the file was moved to the destination specified by the
        # highest-priority rule (`filename:`).
        env.assert_in_lib_dir("Tag Artist/Tag Album/from_filename/track_1.log")

        # Assert that the file does NOT exist in the lower-priority destinations.
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/from_paired/track_1.log")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/from_pattern/track_1.log")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/from_ext/track_1.log")

    def test_rename_wildcard_extension_halts(self) -> None:
        """Ensure that specifying `ext:.*` extensions results in an exception."""
        env = self.env

        env.config["filetote"]["extensions"] = ".file .nfo"
        env.config["paths"]["ext:.*"] = "$albumpath/$old_filename"
        env.config["import"]["move"] = True

        with pytest.raises(AssertionError) as exception_info:
            env.run_cli_command("import")

        assert str(exception_info.value) == _WILDCARD_EXT_ERROR

    def test_rename_filetote_paths_wildcard_extension_halts(self) -> None:
        """Ensure that specifying `ext:.*` in filetote paths results in an
        exception.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".file .nfo"
        env.config["filetote"]["paths"]["ext:.*"] = "$albumpath/$old_filename"
        env.config["import"]["move"] = True

        with pytest.raises(AssertionError) as exception_info:
            env.run_cli_command("import")

        assert str(exception_info.value) == _WILDCARD_EXT_ERROR

    def test_filetote_paths_priority_over_beets_paths(self) -> None:
        """Ensure that the Filetote `paths` settings take priority over any
        matching-specified ones in beets' `paths` settings.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".file"

        env.config["filetote"]["paths"]["filetote:default"] = env.fmt_path(
            "$albumpath", "Filetote", "$old_filename"
        )
        env.config["paths"]["filetote:default"] = env.fmt_path(
            "$albumpath", "beets", "$old_filename"
        )

        env.config["import"]["move"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Filetote/artifact.file")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.file")

    def test_rename_filetote_default(self) -> None:
        """Ensure that the default value for a path query of an otherwise not specified
        artifact is `$albumpath/$old_filename`.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".file"
        env.config["import"]["move"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")

    def test_rename_filetote_custom_default(self) -> None:
        """Ensure that the default value for a path query for artifacts
        (`filetote:default`) can be updated via the root `paths` setting.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".file"
        env.config["paths"]["filetote:default"] = env.fmt_path(
            "$albumpath", "New", "$old_filename"
        )
        env.config["import"]["move"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/New/artifact.file")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.file")

    def test_rename_filetote_custom_default_filetote_paths(self) -> None:
        """Ensure that the default value for a path query for artifacts
        (`filetote:default`) can be updated via the Filetote `paths` setting.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".file"
        env.config["filetote"]["paths"]["filetote:default"] = env.fmt_path(
            "$albumpath", "New", "$old_filename"
        )
        env.config["import"]["move"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/New/artifact.file")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.file")

    def test_rename_filetote_custom_default_priority(self) -> None:
        """Ensure that the default value for a path query for artifacts
        (`filetote:default`) prioritizes the Filetote `paths` setting over the
        root `paths` setting.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".file"
        env.config["paths"]["filetote:default"] = env.fmt_path(
            "$albumpath", "Paths", "$old_filename"
        )
        env.config["filetote"]["paths"]["filetote:default"] = env.fmt_path(
            "$albumpath", "Filetote", "$old_filename"
        )
        env.config["import"]["move"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Filetote/artifact.file")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.file")

    def test_rename_filetote_pairing_custom_default(self) -> None:
        """Ensure that the default value for a path query for artifacts
        (`filetote-pairing:default`) can be updated via the root `paths` setting.
        """
        env = self.env

        env.config["filetote"]["pairing"]["enabled"] = True
        env.config["paths"]["filetote-pairing:default"] = env.fmt_path(
            "$albumpath", "New", "$old_filename"
        )
        env.config["import"]["move"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/New/track_1.lrc")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/track_1.lrc")

    def test_rename_filetote_pairing_custom_default_filetote_paths(self) -> None:
        """Ensure that the default value for a path query for artifacts
        (`filetote-pairing:default`) can be updated via the Filetote `paths` setting.
        """
        env = self.env

        env.config["filetote"]["pairing"]["enabled"] = True
        env.config["filetote"]["paths"]["filetote-pairing:default"] = env.fmt_path(
            "$albumpath", "New", "$old_filename"
        )
        env.config["import"]["move"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/New/track_1.lrc")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/track_1.lrc")

    def test_rename_respect_defined_order(self) -> None:
        """Tests that patterns respect the defined order and priority."""
        env = self.env
        album_path = env.import_dir / "the_album"

        env.create_file(album_path / "scans" / "scan-1.jpg")
        env.create_file(album_path / "cover.jpg")
        env.create_file(album_path / "sub.cue")
        env.create_file(album_path / "md5.sum")

        env.config["filetote"]["extensions"] = ".*"
        env.config["filetote"]["exclude"] = {"extensions": [".sum"]}

        env.config["filetote"]["patterns"] = {
            "scans": ["[sS]cans/"],
            "artwork": ["[sS]cans/"],
            "cover": ["*.jpg"],
            "cue": ["*.cue"],
        }

        env.config["paths"] = {
            "pattern:cover": env.fmt_path(
                "$albumpath", "${album} - $old_filename - cover"
            ),
            "filetote:default": env.fmt_path("$albumpath", "default", "$old_filename"),
            "pattern:cue": env.fmt_path("$albumpath", "${album} - $old_filename - cue"),
        }

        env.config["filetote"]["paths"] = {
            "pattern:artwork": env.fmt_path("$albumpath", "$old_filename - artwork"),
            "pattern:scans": env.fmt_path("$albumpath", "scans", "$old_filename"),
        }

        env.run_cli_command("import")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/Artwork/md5.sum")
        env.assert_in_lib_dir("Tag Artist/Tag Album/scans/scan-1.jpg")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Album - sub - cue.cue")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Album - cover - cover.jpg")
