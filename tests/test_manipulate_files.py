import logging
import os
import stat
import sys

import pytest
from beets import config, util

import tests._common as _common
from tests.helper import CopyFileArtifactsTestCase

log = logging.getLogger("beets")


class CopyFileArtifactsManipulateFiles(CopyFileArtifactsTestCase):
    """
    Tests to check that copyfileartifacts renames as expected for custom path
    formats (both by extension and filename).
    """

    def setUp(self):
        super(CopyFileArtifactsManipulateFiles, self).setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False, copy=False)

    @pytest.mark.skipif(not _common.HAVE_SYMLINK, reason="need symlinks")
    def test_import_symlink_files(self):
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
            b"newname.file",
        )

        self._run_importer()

        self.assert_in_import_dir(b"the_album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"newname.file")

        self.assert_islink(b"Tag Artist", b"Tag Album", b"newname.file")

        self.assert_equal_path(
            util.bytestring_path(os.readlink(new_path)), old_path
        )

    @pytest.mark.skipif(not _common.HAVE_HARDLINK, reason="need hardlinks")
    def test_import_hardlink_files(self):
        config["copyfileartifacts"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/newname")
        config["import"]["hardlink"] = True

        old_path = os.path.join(
            self.import_dir,
            b"the_album",
            b"artifact.file",
        )

        new_path = os.path.join(
            self.lib_dir,
            b"Tag Artist",
            b"Tag Album",
            b"newname.file",
        )

        self._run_importer()

        self.assert_in_import_dir(b"the_album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"newname.file")

        s1 = os.stat(old_path)
        s2 = os.stat(new_path)
        self.assertTrue(
            (s1[stat.ST_INO], s1[stat.ST_DEV])
            == (s2[stat.ST_INO], s2[stat.ST_DEV])
        )

    @pytest.mark.skipif(not _common.HAVE_REFLINK, reason="need reflinks")
    def test_import_reflink_files(self):
        config["copyfileartifacts"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/newname")
        config["import"]["reflink"] = True

        old_path = os.path.join(
            self.import_dir,
            b"the_album",
            b"artifact.file",
        )

        new_path = os.path.join(
            self.lib_dir,
            b"Tag Artist",
            b"Tag Album",
            b"newname.file",
        )

        self._run_importer()

        self.assert_in_import_dir(b"the_album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"newname.file")
