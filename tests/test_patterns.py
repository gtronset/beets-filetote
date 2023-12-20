"""Tests "pattern" functionality for the beets-filetote plugin."""

import logging
import os
from typing import List, Optional

from beets import config

from tests.helper import FiletoteTestCase, capture_log

log = logging.getLogger("beets")


class FiletotePatternTest(FiletoteTestCase):
    """
    Tests to check that Filetote grabs artfacts by user-definited patterns.
    """

    def setUp(self, other_plugins: Optional[List[str]] = None) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

    def test_patterns_match_all_glob(self) -> None:
        """Tests that the `*.*` pattern matches all artifacts."""
        config["filetote"]["patterns"] = {
            "all-pattern": ["*.*"],
        }

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_2.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_3.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")

    def test_patterns_match(self) -> None:
        """Tests that patterns are used to itentify artifacts."""
        config["filetote"]["patterns"] = {
            "file-pattern": ["[aA]rtifact.file", "artifact[23].file"],
            "nfo-pattern": ["*.nfo"],
        }

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")

    def test_patterns_subfolders_match(self) -> None:
        """Tests that patterns can match subdirectories/subfolders."""

        artwork_dir = os.path.join(self.import_dir, b"the_album", b"artwork")
        os.makedirs(artwork_dir)

        self.create_file(
            path=artwork_dir,
            filename=b"cover.jpg",
        )

        config["filetote"]["patterns"] = {
            "file-pattern": ["/[aA]rtifact.file", "artifact[23].file"],
            "subfolder-pattern": ["/[aA]rtwork/cover.jpg"],
        }

        config["paths"]["pattern:subfolder-pattern"] = os.path.join(
            b"$albumpath", b"artwork", b"$old_filename"
        )

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artwork", b"cover.jpg")

    def test_patterns_of_folders_grab_all_files(self) -> None:
        """Tests that patterns of just folders grab all contents."""

        artwork_dir = os.path.join(self.import_dir, b"the_album", b"artwork")
        cd1_dir = os.path.join(self.import_dir, b"the_album", b"CD1")
        subfolder_dir = os.path.join(
            self.import_dir, b"the_album", b"Subfolder1", b"Subfolder2", b"Subfolder3"
        )
        os.makedirs(artwork_dir)
        os.makedirs(cd1_dir)
        os.makedirs(subfolder_dir)

        self.create_file(
            path=artwork_dir,
            filename=b"cover.jpg",
        )
        self.create_file(
            path=cd1_dir,
            filename=b"cd.file",
        )
        self.create_file(
            path=subfolder_dir,
            filename=b"sub.file",
        )

        config["filetote"]["patterns"] = {
            "subfolder1-pattern": ["[aA]rtwork/"],
            "subfolder2-pattern": ["CD1/*.*"],
            "subfolder3-pattern": ["Subfolder1/Subfolder2/"],
        }

        config["paths"]["pattern:subfolder1-pattern"] = os.path.join(
            b"$albumpath", b"artwork", b"$old_filename"
        )

        config["paths"]["pattern:subfolder3-pattern"] = os.path.join(
            b"$albumpath", b"sub1", b"sub2", b"$old_filename"
        )

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artwork", b"cover.jpg")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"cd.file")
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"sub1", b"sub2", b"sub.file"
        )

    def test_patterns_path_renaming(self) -> None:
        """Tests that the path definition for `pattern:` prefix works."""
        config["filetote"]["patterns"] = {
            "file-pattern": ["[Aa]rtifact.file", "artifact[23].file"],
            "nfo-pattern": ["*.nfo"],
        }
        config["paths"][
            "pattern:file-pattern"
        ] = "$albumpath/file-pattern $old_filename"

        config["paths"]["pattern:nfo-pattern"] = "$albumpath/nfo-pattern $old_filename"

        with capture_log() as logs:
            self._run_cli_command("import")

        for line in logs:
            if line.startswith("filetote:"):
                log.info(line)

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"file-pattern artifact.file"
        )
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"file-pattern artifact2.file"
        )
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"nfo-pattern artifact.nfo")
