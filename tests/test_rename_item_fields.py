"""Tests renaming Item fields for the beets-filetote plugin."""

import logging

from beets import config

from tests.helper import FiletoteTestCase

log = logging.getLogger("beets")


class FiletoteRenameItemFieldsTest(FiletoteTestCase):
    """
    Tests to check that Filetote renames using default Item fields as
    expected for custom path formats.
    """

    def setUp(self, audible_plugin: bool = False) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

    def test_rename_core_item_fields(self) -> None:
        """
        Tests that the value of `title, `artist`, `albumartist`, and `album`
        populate in renaming.
        """
        config["filetote"]["extensions"] = ".file"
        config["paths"][
            "ext:file"
        ] = "$albumpath/$artist - $album - $track $title ($albumartist) newname"

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist",
            b"Tag Album",
            b"Tag Artist - Tag Album - 01 Tag Title 1 (Tag Album Artist) newname.file",
        )

    def test_rename_other_meta_item_fields(self) -> None:
        """
        Tests that the value of `year, `month`, `day`, `$track, `tracktotal`
        and `disc`, and `disctotal` populate in renaming.
        """
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = (
            "$albumpath/($year-$month-$day) - Track $track of $tracktotal - Disc $disc"
            " of $disctotal"
        )

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist",
            b"Tag Album",
            b"(2023-02-03) - Track 01 of 05 - Disc 01 of 07.file",
        )

    def test_rename_lyric_comment_item_fields(self) -> None:
        """
        Tests that the value of `lyric` and `comments` populate in renaming.
        """
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = "$albumpath/$lyrics ($comments)"

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist",
            b"Tag Album",
            b"Tag lyrics (Tag comments).file",
        )

    def test_rename_track_music_item_fields(self) -> None:
        """
        Tests that the value of `bpm`, `length`, `format`, and `bitrate` populate
        in renaming.

        `length` will convert from `M:SS` to `M_SS` for path-friendliness.
        """
        config["filetote"]["extensions"] = ".file"
        config["paths"][
            "ext:file"
        ] = "$albumpath/newname - ${bpm}bpm $length ($format) ($bitrate)"

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist",
            b"Tag Album",
            b"newname - 8bpm 0_01 (MP3) (80kbps).file",
        )

    def test_rename_mb_item_fields(self) -> None:
        """
        Tests that the value of `mb_albumid, `mb_artistid`,
        `mb_albumartistid`, `mb_trackid`, `mb_releasetrackid`,
        and `mb_workid` populate in renaming.
        """
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = (
            "$albumpath/$mb_artistid - $mb_albumid ($mb_albumartistid) - $mb_trackid"
            " $mb_releasetrackid - $mb_workid"
        )

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist",
            b"Tag Album",
            b"someID-3 - someID-2 (someID-4) - someID-1 someID-5 - Tag work"
            b" musicbrainz id.file",
        )
