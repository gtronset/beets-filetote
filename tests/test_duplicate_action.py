"""Tests `duplicate_action` config for the beets-filetote plugin."""

import logging

from beets import config

from tests.helper import FiletoteTestCase, capture_log_with_traceback

log = logging.getLogger("beets")


class FiletoteReimportTest(FiletoteTestCase):
    """Tests to check that Filetote handles reimports correctly."""

    def setUp(self, _other_plugins: list[str] | None = None) -> None:
        """Setup subsequent import directory of the below structure.

        Ex:
        testlib_dir/
            Tag Artist/
                Tag Album/
                    Tag Title 1.mp3
                    Tag Title 2.mp3
                    Tag Title 3.mp3
                    artifact.file
                    artifact2.file
        """
        super().setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False, move=True)

        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = self.fmt_path("$albumpath", "$old_filename")

        log.debug("--- initial import")
        self._run_cli_command("import")

    def test_duplicate_action_default(self) -> None:
        """Tests that when `duplicate_action` default when not specified is 'merge',
        that a debug message is logged, and Filetote does not overwrite or rename the
        file if it is the same in name and identical in content, but if the content is
        different, it renames the new file to be unique (e.g., artifact.1.file).
        """
        with capture_log_with_traceback("beets.filetote") as logs:
            log.debug("--- second import")

            self._create_flat_import_dir()

            (self.import_dir / "the_album" / "artifact.file").write_text("NEW CONTENT")

            self._run_cli_command("import")

        assert any(
            "Skipping artifact `artifact2.file`" in line and "already exists" in line
            for line in logs
        )

        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.1.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")

        self.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact2.1.file")

    def test_duplicate_action_merge(self) -> None:
        """Tests that when `duplicate_action` is 'merge', that a debug message is
        logged, and Filetote does not overwrite or rename the file if it is the same in
        name and identical in content, but if the content is different, it renames the
        new file to be unique (e.g., artifact.1.file).
        """
        with capture_log_with_traceback("beets.filetote") as logs:
            log.debug("--- second import")

            self._create_flat_import_dir()

            (self.import_dir / "the_album" / "artifact.file").write_text("NEW CONTENT")

            self._run_cli_command("import")

        assert any(
            "Skipping artifact `artifact2.file`" in line and "already exists" in line
            for line in logs
        )

        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.1.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")

        self.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact2.1.file")

    def test_duplicate_action_skip(self) -> None:
        """Tests that when `duplicate_action` is 'skip', that a debug message
        is logged, and Filetote does not overwrite or rename the file.
        """
        config["filetote"]["duplicate_action"] = "skip"

        with capture_log_with_traceback("beets.filetote") as logs:
            log.debug("--- second import")

            self._create_flat_import_dir()

            self._run_cli_command("import")

        skipped_logs = [
            line
            for line in logs
            if "Skipping artifact" in line and "already exists" in line
        ]

        assert any("Skipping artifact `artifact.file`" in line for line in skipped_logs)
        assert any(
            "Skipping artifact `artifact2.file`" in line for line in skipped_logs
        )

        expected_count: int = 2

        assert len(skipped_logs) == expected_count

        self.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.1.file")

    def test_duplicate_action_keep(self) -> None:
        """Tests that when `duplicate_action` is 'keep', the incoming artifact is
        renamed to be unique (e.g., artifact.1.file).
        """
        config["filetote"]["duplicate_action"] = "keep"

        with capture_log_with_traceback("beets.filetote") as logs:
            log.debug("--- second import")

            self._create_flat_import_dir()

            self._run_cli_command("import")

        assert not any(
            "Skipping artifact" in line and "already exists" in line for line in logs
        )

        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.1.file")

    def test_duplicate_action_remove(self) -> None:
        """Tests that when `duplicate_action` is 'remove', we overwrite the
        existing artifact with the new one.
        """
        config["filetote"]["duplicate_action"] = "remove"

        with capture_log_with_traceback("beets.filetote") as logs:
            log.debug("--- second import")

            self._create_flat_import_dir()

            (self.import_dir / "the_album" / "artifact.file").write_text("NEW CONTENT")

            self._run_cli_command("import")

        assert not any(
            "Skipping artifact" in line and "already exists" in line for line in logs
        )

        dest_file = self.lib_dir / "Tag Artist/Tag Album/artifact.file"
        assert dest_file.read_text() == "NEW CONTENT"

        self.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.1.file")
