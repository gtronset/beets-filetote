"""Tests `duplicate_action` config for the Filetote plugin."""

import pytest

from tests.pytest_beets_plugin import BeetsEnvFactory


class TestDuplicateAction:
    """Tests to check that Filetote handles reimports correctly."""

    @pytest.fixture(autouse=True)
    def _setup(self, beets_flat_env: BeetsEnvFactory) -> None:
        """Perform an initial import so each test starts with artifacts in the
        library.

        Library structure after setup:

            testlib_dir/
                Tag Artist/
                    Tag Album/
                        Tag Title 1.mp3
                        Tag Title 2.mp3
                        Tag Title 3.mp3
                        artifact.file
                        artifact2.file
        """
        self.env = beets_flat_env(move=True)
        env = self.env

        env.config["filetote"]["extensions"] = ".file"
        env.config["paths"]["ext:file"] = env.fmt_path("$albumpath", "$old_filename")

        # "keep" is safe here since the first import has no duplicates to resolve.
        env.config["import"]["duplicate_action"] = "keep"

        env.log.debug("--- initial import")
        env.run_cli_command("import")

    def _reimport(self, modify_artifact: str | None = None) -> None:
        """Create a fresh import dir and run a second import.

        Args:
            modify_artifact: If provided, overwrite this file with new content before
                reimporting, so the duplicate has different content.
        """
        env = self.env

        env.create_flat_import_dir()

        if modify_artifact:
            (env.import_dir / "the_album" / modify_artifact).write_text("NEW CONTENT")

        env.run_cli_command("import")

    def test_duplicate_action_default(self) -> None:
        """Tests that when `duplicate_action` is not specified (defaults to `merge`),
        Filetote skips identical files and renames files with different content to be
        unique (e.g., `artifact.1.file`).
        """
        env = self.env

        with env.capture_log("beets.filetote") as logs:
            env.log.debug("--- second import")
            self._reimport(modify_artifact="artifact.file")

        assert any(
            "Skipping artifact `artifact2.file`" in line and "already exists" in line
            for line in logs
        )

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.1.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact2.1.file")

    def test_duplicate_action_merge(self) -> None:
        """Tests that when `duplicate_action` is 'merge', Filetote skips
        identical files and renames files with different content to be unique
        (e.g., `artifact.1.file`).
        """
        env = self.env

        env.config["import"]["duplicate_action"] = "merge"
        env.config["filetote"]["duplicate_action"] = "merge"

        with env.capture_log("beets.filetote") as logs:
            env.log.debug("--- second import")
            self._reimport(modify_artifact="artifact.file")

        assert any(
            "Skipping artifact `artifact2.file`" in line and "already exists" in line
            for line in logs
        )

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.1.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact2.1.file")

    def test_duplicate_action_skip(self) -> None:
        """Tests that when `duplicate_action` is 'skip', Filetote logs a message and
        does not overwrite or rename the file.
        """
        env = self.env

        # The Item needs to be copied/moved still for the artifacts to be processed
        env.config["import"]["duplicate_action"] = "keep"
        env.config["filetote"]["duplicate_action"] = "skip"

        with env.capture_log("beets.filetote") as logs:
            env.log.debug("--- second import")
            self._reimport()

        skipped_logs = [
            line
            for line in logs
            if "Skipping artifact" in line and "already exists" in line
        ]

        expected_skips = [
            "artifact.file",
            "artifact2.file",
        ]

        for name in expected_skips:
            assert any(f"Skipping artifact `{name}`" in line for line in skipped_logs)

        assert len(skipped_logs) == len(expected_skips)

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.1.file")

    def test_duplicate_action_keep(self) -> None:
        """Tests that when `duplicate_action` is 'keep', the incoming artifact is
        renamed to be unique (e.g., `artifact.1.file`).
        """
        env = self.env

        env.config["import"]["duplicate_action"] = "keep"
        env.config["filetote"]["duplicate_action"] = "keep"

        with env.capture_log("beets.filetote") as logs:
            env.log.debug("--- second import")
            self._reimport()

        assert not any(
            "Skipping artifact" in line and "already exists" in line for line in logs
        )

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.1.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.1.file")

    def test_duplicate_action_remove(self) -> None:
        """Tests that when `duplicate_action` is 'remove', the existing artifact is
        overwritten with the new one.
        """
        env = self.env

        env.config["import"]["duplicate_action"] = "remove"
        env.config["filetote"]["duplicate_action"] = "remove"

        with env.capture_log("beets.filetote") as logs:
            env.log.debug("--- second import")
            self._reimport(modify_artifact="artifact.file")

        assert not any(
            "Skipping artifact" in line and "already exists" in line for line in logs
        )

        dest_file = env.lib_dir / "Tag Artist/Tag Album/artifact.file"
        assert dest_file.read_text() == "NEW CONTENT"

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.1.file")
