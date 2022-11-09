import logging
import os
import sys

import pytest
from beets import config, util

import tests._common as _common
from tests.helper import CopyFileArtifactsTestCase

log = logging.getLogger("beets")


class CopyFileArtifactsManipulate(CopyFileArtifactsTestCase):
    """
    Tests to check that copyfileartifacts renames as expected for custom path
    formats (both by extension and filename).
    """

    def setUp(self):
        super(CopyFileArtifactsManipulate, self).setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False, copy=False)

    @pytest.mark.skipif(not _common.HAVE_SYMLINK, reason="need symlinks")
    def test_import_link_arrives(self):
        config["copyfileartifacts"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/newname")
        config["import"]["link"] = True

        old_path = os.path.join(
            self.import_dir,
            b"the_album",
            b"artifact.file",
        )

        new_path = os.path.join(
            self.lib_dir,
            b"Tag Artist",
            b"Tag Album",
            b"newname.files",
        )

        new_track_path = os.path.join(
            self.lib_dir,
            b"Tag Artist",
            b"Tag Album",
            b"Track 1.mp3",
        )

        self._run_importer()
        log.debug(f"is link: {0}", os.path.islink(new_track_path))
        log.debug(f"is link: {0}", os.path.islink(new_path))
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"newname.file")
        self.assert_islink(b"Tag Artist", b"Tag Album", b"newname.file")
        self.assert_equal_path(
            util.bytestring_path(os.readlink(new_path)), old_path
        )

    # @pytest.mark.skipif(not _common.HAVE_HARDLINK, reason="need hardlinks")
    # def test_import_hardlink_arrives(self):
    #     config["import"]["hardlink"] = True
    #     self.importer.run()
    #     for mediafile in self.import_media:
    #         filename = os.path.join(
    #             self.libdir,
    #             b"Tag Artist",
    #             b"Tag Album",
    #             util.bytestring_path(f"{mediafile.title}.mp3"),
    #         )
    #         self.assertExists(filename)
    #         s1 = os.stat(mediafile.path)
    #         s2 = os.stat(filename)
    #         self.assertTrue(
    #             (s1[stat.ST_INO], s1[stat.ST_DEV])
    #             == (s2[stat.ST_INO], s2[stat.ST_DEV])
    #         )
