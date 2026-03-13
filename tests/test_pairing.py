"""Tests pairing for the beets-filetote plugin."""

from tests.pytest_beets_plugin import MediaSetup
from tests.pytest_beets_plugin.fixtures import BeetsEnvFactory


class TestPairing:
    """Tests to check that Filetote handles "pairs" of files."""

    def test_pairing_default_is_disabled(self, beets_flat_env: BeetsEnvFactory) -> None:
        """Ensure that, by default, pairing is disabled."""
        env = beets_flat_env(media_files=[MediaSetup(count=1)])

        env.config["filetote"]["extensions"] = ".lrc"

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/track_1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_pairingonly_requires_pairing_enabled(
        self, beets_flat_env: BeetsEnvFactory
    ) -> None:
        """Test that without `enabled`, `pairing_only` does nothing."""
        env = beets_flat_env()

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"] = {
            "enabled": False,
            "pairing_only": True,
        }

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/track_1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_pairing_disabled_copies_all_matches(
        self, beets_flat_env: BeetsEnvFactory
    ) -> None:
        """Ensure that when pairing is disabled it does not do anything with pairs."""
        env = beets_flat_env(media_files=[MediaSetup(count=1)])

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"]["enabled"] = False

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/track_1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_pairing_enabled_copies_all_matches(
        self, beets_flat_env: BeetsEnvFactory
    ) -> None:
        """Ensure that all pairs are copied."""
        env = beets_flat_env(media_files=[MediaSetup(count=2)])

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"]["enabled"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 2.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_paired_file_for_second_item_is_handled_once(
        self, beets_flat_env: BeetsEnvFactory
    ) -> None:
        """Tests that a paired file for a later item in an album is claimed
        correctly from the shared pool and not processed twice.
        """
        env = beets_flat_env(media_files=[MediaSetup(count=2)])

        env.config["filetote"]["pairing"]["enabled"] = True
        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["exclude"] = ["artifact.lrc"]
        env.config["filetote"]["paths"] = {
            "paired_ext:lrc": "$albumpath/${medianame_new}-paired",
            "ext:lrc": "$albumpath/${medianame_new}-generic",
        }

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 2-paired.lrc")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/Tag Title 1-generic.lrc")

    def test_pairing_enabled_works_without_pairs(
        self, beets_flat_env: BeetsEnvFactory
    ) -> None:
        """Ensure that even when there's not a pair, other files can be handled."""
        env = beets_flat_env(media_files=[MediaSetup(count=1, generate_pair=False)])

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"]["enabled"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_pairing_does_not_require_pairs_for_all_media(
        self, beets_flat_env: BeetsEnvFactory
    ) -> None:
        """Ensure that when there's not a pair, other paired files still copy."""
        env = beets_flat_env(media_files=[MediaSetup(count=2, generate_pair=False)])

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"]["enabled"] = True

        env.create_file(env.import_dir / "the_album" / "track_1.lrc")

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_pairingonly_disabled_copies_all_matches(
        self, beets_flat_env: BeetsEnvFactory
    ) -> None:
        """Ensure that `pairing_only` disabled allows other matches to an
        extension to be handled.
        """
        env = beets_flat_env(media_files=[MediaSetup(count=2)])

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"] = {
            "enabled": True,
            "pairing_only": False,
        }

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 2.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_pairingonly_processes_just_pairs(
        self, beets_flat_env: BeetsEnvFactory
    ) -> None:
        """Test that `pairing_only` means that only pairs meeting a certain
        extension are handled.
        """
        env = beets_flat_env(media_files=[MediaSetup(count=2)])

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"] = {
            "enabled": True,
            "pairing_only": True,
        }

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 2.lrc")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_pairingonly_does_not_require_pairs_for_all_media(
        self, beets_flat_env: BeetsEnvFactory
    ) -> None:
        """Ensure that `pairing_only` does not require all media files for pairs to
        move/copy.
        """
        env = beets_flat_env(media_files=[MediaSetup(count=2, generate_pair=False)])

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"] = {
            "enabled": True,
            "pairing_only": True,
        }

        env.create_file(env.import_dir / "the_album" / "track_1.lrc")

        env.run_cli_command("import")

        env.assert_in_import_dir("the_album/track_1.lrc")
        env.assert_in_import_dir("the_album/artifact.lrc")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_pairing_extensions(self, beets_flat_env: BeetsEnvFactory) -> None:
        """Ensure that paired extensions are seen and manipulated."""
        env = beets_flat_env(media_files=[MediaSetup(count=2, generate_pair=False)])

        env.config["filetote"]["pairing"] = {
            "enabled": True,
            "pairing_only": True,
            "extensions": ".lrc .kar",
        }

        album_path = env.import_dir / "the_album"
        for filename in ["track_1.kar", "track_1.lrc", "track_1.jpg"]:
            env.create_file(album_path / filename)

        env.run_cli_command("import")

        env.assert_in_import_dir("the_album/track_1.lrc")
        env.assert_in_import_dir("the_album/artifact.lrc")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.kar")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/track_1.jpg")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_pairing_extensions_are_additive_to_toplevel_extensions(
        self, beets_flat_env: BeetsEnvFactory
    ) -> None:
        """Ensure that those extensions defined in pairing extend any extensions
        defined in the `extensions` config.
        """
        env = beets_flat_env(media_files=[MediaSetup(count=2, generate_pair=False)])

        env.config["filetote"]["extensions"] = ".jpg"
        env.config["filetote"]["pairing"] = {
            "enabled": True,
            "extensions": ".lrc",
        }

        album_path = env.import_dir / "the_album"
        for filename in ["track_1.kar", "track_1.lrc", "track_1.jpg"]:
            env.create_file(album_path / filename)

        env.run_cli_command("import")

        env.assert_in_import_dir("the_album/track_1.lrc")
        env.assert_in_import_dir("the_album/artifact.lrc")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/track_1.jpg")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/track_1.kar")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")
