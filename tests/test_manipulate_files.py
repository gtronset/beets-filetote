"""Tests manipulation of files for the beets-filetote plugin."""

import logging
import os
import stat

import pytest
from beets import config, util

from tests import _common
from tests.helper import FiletoteTestCase

log = logging.getLogger("beets")


class FiletoteManipulateFiles(FiletoteTestCase):
    """
    Tests to check that Filetote manipulates files using the correct operation.
    """

    def setUp(self):
        """Provides shared setup for tests."""
        super().setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False, copy=False)

    @pytest.mark.skipif(not _common.HAVE_SYMLINK, reason="need symlinks")
    def test_import_symlink_files(self):
        """Tests that the `symlink` operation correctly symlinks files."""
        config["filetote"]["extensions"] = ".file"
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
        """Tests that the `hardlink` operation correctly hardlinks files."""

        config["filetote"]["extensions"] = ".file"
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

        stat_old_path = os.stat(old_path)
        stat_new_path = os.stat(new_path)
        self.assertTrue(
            (stat_old_path[stat.ST_INO], stat_old_path[stat.ST_DEV])
            == (stat_new_path[stat.ST_INO], stat_new_path[stat.ST_DEV])
        )

    @pytest.mark.skipif(not _common.HAVE_REFLINK, reason="need reflinks")
    def test_import_reflink_files(self):
        """Tests that the `reflink` operation correctly links files."""

        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/newname")
        config["import"]["reflink"] = True

        self._run_importer()

        self.assert_in_import_dir(b"the_album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"newname.file")
