import os
import sys

import beets
from beets import config

from tests.helper import CopyFileArtifactsTestCase


class CopyFileArtifactsFilename(CopyFileArtifactsTestCase):
    """
    Tests to check handling of artifacts with filenames containing unicode characters
    """

    def setUp(self):
        super(CopyFileArtifactsFilename, self).setUp()

        self._set_import_dir()
        self.album_path = os.path.join(self.import_dir, b"the_album")
        os.makedirs(self.album_path)

        self._setup_import_session(autotag=False)

        config["copyfileartifacts"]["extensions"] = ".file"

    def test_import_dir_with_unicode_character_in_artifact_name_copy(self):
        open(
            os.path.join(
                self.album_path, beets.util.bytestring_path("\xe4rtifact.file")
            ),
            "a",
        ).close()
        medium = self._create_medium(
            os.path.join(self.album_path, b"track_1.mp3"), b"full.mp3"
        )
        self.import_media = [medium]

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist",
            b"Tag Album",
            beets.util.bytestring_path("\xe4rtifact.file"),
        )

    def test_import_dir_with_unicode_character_in_artifact_name_move(self):
        config["import"]["move"] = True

        open(
            os.path.join(
                self.album_path, beets.util.bytestring_path("\xe4rtifact.file")
            ),
            "a",
        ).close()
        medium = self._create_medium(
            os.path.join(self.album_path, b"track_1.mp3"), b"full.mp3"
        )
        self.import_media = [medium]

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist",
            b"Tag Album",
            beets.util.bytestring_path("\xe4rtifact.file"),
        )

    def test_import_dir_with_illegal_character_in_album_name(self):
        config["paths"]["ext:file"] = str("$albumpath/$artist - $album")

        # Create import directory, illegal filename character used in the album name
        open(os.path.join(self.album_path, b"artifact.file"), "a").close()
        medium = self._create_medium(
            os.path.join(self.album_path, b"track_1.mp3"),
            b"full.mp3",
            b"Tag Album?",
        )
        self.import_media = [medium]

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album_", b"Tag Artist - Tag Album_.file"
        )
