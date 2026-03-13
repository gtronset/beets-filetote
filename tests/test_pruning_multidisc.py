"""Tests pruning of multi-disc imports for the beets-filetote plugin."""

from tests.pytest_beets_plugin import BeetsEnvFactory


class TestPruningMultiDisc:
    """Tests to check that Filetote correctly "prunes" directories when
    it moves artifact files from nested (multi-disc) imports.
    """

    def test_prunes_multidisc_nested(self, beets_nested_env: BeetsEnvFactory) -> None:
        """Ensures that multidisc nested directories are pruned correctly on move."""
        env = beets_nested_env(move=True)

        env.config["filetote"]["extensions"] = ".*"

        env.run_cli_command("import")

        env.assert_not_in_import_dir("the_album/disc1")
        env.assert_not_in_import_dir("the_album/disc2")
        env.assert_not_in_import_dir("the_album")
