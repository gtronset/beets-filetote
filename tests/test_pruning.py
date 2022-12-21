import logging
import os

from beets import config

from tests.helper import FiletoteTestCase

log = logging.getLogger("beets")


class FiletotePruningyTest(FiletoteTestCase):
    """
    Tests to check that Filetote correctly "prunes" directories when
    it moves artifact files.
    """

    def setUp(self):
        super(FiletotePruningyTest, self).setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False, move=True)

    def test_prune_import_directory_when_emptied(self):
        """
        Check that plugin does not interfere with normal
        pruning of emptied import directories.
        """
        config["filetote"]["extensions"] = ".*"

        self._run_importer()

        self.assert_import_dir_exists()
        self.assert_not_in_import_dir(b"the_album")

    def test_prune_import_subdirectory_only_not_above(self):
        """
        Check that plugin only prunes nested folder when specified.
        """
        self._setup_import_session(
            autotag=False,
            import_dir=os.path.join(self.import_dir, b"the_album"),
            move=True,
        )
        config["filetote"]["extensions"] = ".*"
        self._run_importer()

        self.assert_import_dir_exists(self.import_dir)
        self.assert_not_in_import_dir(b"the_album")

    def test_prune_import_expands_user_import_path(self):
        """
        Check that plugin prunes and converts/expands the user parts of path if
        present.
        """
        self._setup_import_session(
            autotag=False,
            import_dir=os.path.join(self.import_dir, b"the_album"),
            move=True,
        )
        config["filetote"]["extensions"] = ".*"
        self._run_importer()

        self.assert_import_dir_exists(self.import_dir)
        self.assert_not_in_import_dir(b"the_album")

    def test_prune_reimport(self):
        """
        Check that plugin prunes to the root of the library when reimporting
        from library.

        Setup subsequent import directory of the following structure:

            testlib_dir/
                Tag Artist/
                    Tag Album/
                        Tag Title 1.mp3
                        Tag Title 2.mp3
                        Tag Title 3.mp3
                        artifact.file
                        artifact2.file
        """

        config["filetote"]["extensions"] = ".file"

        log.debug("--- initial import")
        self._run_importer()

        self.lib.path_formats[0] = (
            "default",
            os.path.join("1$artist", "$album", "$title"),
        )
        self._setup_import_session(
            autotag=False, import_dir=self.lib_dir, move=True
        )

        log.debug("--- second import")

        self._run_importer()

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album")
        self.assert_not_in_lib_dir(b"Tag Artist")
        self.assert_in_lib_dir(b"1Tag Artist", b"Tag Album", b"artifact.file")
