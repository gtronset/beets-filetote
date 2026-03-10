"""Tests pairing for the beets-filetote plugin."""

from typing import TYPE_CHECKING

import pytest

from tests.pytest_beets_plugin import MediaSetup

if TYPE_CHECKING:
    from tests.pytest_beets_plugin.plugin_fixture import BeetsPluginFixture


class TestPairing:
    """Tests to check that Filetote handles "pairs" of files."""

    @pytest.fixture(autouse=True)
    def _setup(self, beets_plugin_env: "BeetsPluginFixture") -> None:
        """Provides shared setup for tests."""
        self.env = beets_plugin_env

    def test_pairing_default_is_disabled(self) -> None:
        """Ensure that, by default, pairing is disabled."""
        env = self.env

        env.create_flat_import_dir(media_files=[MediaSetup(count=1)])
        env.setup_import_session(autotag=False)

        env.config["filetote"]["extensions"] = ".lrc"

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/track_1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_pairingonly_requires_pairing_enabled(self) -> None:
        """Test that without `enabled`, `pairing_only` does nothing."""
        env = self.env

        env.create_flat_import_dir()
        env.setup_import_session(autotag=False)

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"] = {
            "enabled": False,
            "pairing_only": True,
        }

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/track_1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_pairing_disabled_copies_all_matches(self) -> None:
        """Ensure that when pairing is disabled it does not do anything with pairs."""
        env = self.env

        env.create_flat_import_dir(media_files=[MediaSetup(count=1)])
        env.setup_import_session(autotag=False)

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"]["enabled"] = False

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/track_1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_pairing_enabled_copies_all_matches(self) -> None:
        """Ensure that all pairs are copied."""
        env = self.env

        env.create_flat_import_dir(media_files=[MediaSetup(count=2)])
        env.setup_import_session(autotag=False)

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"]["enabled"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 2.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_paired_file_for_second_item_is_handled_once(self) -> None:
        """Tests that a paired file for a later item in an album is claimed
        correctly from the shared pool and not processed twice.
        """
        env = self.env

        env.create_flat_import_dir(media_files=[MediaSetup(count=2)])
        env.setup_import_session(autotag=False)

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
        env.assert_not_in_lib_dir("the_album/track_2.lrc")

    def test_pairing_enabled_works_without_pairs(self) -> None:
        """Ensure that even when there's not a pair, other files can be handled."""
        env = self.env

        env.create_flat_import_dir(
            media_files=[MediaSetup(count=1, generate_pair=False)]
        )
        env.setup_import_session(autotag=False)

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"]["enabled"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_pairing_does_not_require_pairs_for_all_media(self) -> None:
        """Ensure that when there's not a pair, other paired files still copy."""
        env = self.env

        album_path = env.create_flat_import_dir(
            media_files=[MediaSetup(count=2, generate_pair=False)]
        )
        env.setup_import_session(autotag=False)

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"]["enabled"] = True

        env.create_file(album_path / "track_1.lrc")

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_pairingonly_disabled_copies_all_matches(self) -> None:
        """Ensure that `pairing_only` disabled allows other matches to an
        extension to be handled.
        """
        env = self.env

        env.create_flat_import_dir(media_files=[MediaSetup(count=2)])
        env.setup_import_session(autotag=False)

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"] = {
            "enabled": True,
            "pairing_only": False,
        }

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 2.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_pairingonly_processes_just_pairs(self) -> None:
        """Test that `pairing_only` means that only pairs meeting a certain
        extension are handled.
        """
        env = self.env

        env.create_flat_import_dir(media_files=[MediaSetup(count=2)])
        env.setup_import_session(autotag=False)

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"] = {
            "enabled": True,
            "pairing_only": True,
        }

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 2.lrc")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_pairingonly_does_not_require_pairs_for_all_media(self) -> None:
        """Ensure that `pairing_only` does not require all media files for pairs to
        move/copy.
        """
        env = self.env

        album_path = env.create_flat_import_dir(
            media_files=[MediaSetup(count=2, generate_pair=False)]
        )
        env.setup_import_session(autotag=False)

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"] = {
            "enabled": True,
            "pairing_only": True,
        }

        env.create_file(album_path / "track_1.lrc")

        env.run_cli_command("import")

        env.assert_in_import_dir("the_album/track_1.lrc")
        env.assert_in_import_dir("the_album/artifact.lrc")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_pairing_extensions(self) -> None:
        """Ensure that paired extensions are seen and manipulated."""
        env = self.env

        album_path = env.create_flat_import_dir(
            media_files=[MediaSetup(count=2, generate_pair=False)]
        )
        env.setup_import_session(autotag=False)

        env.config["filetote"]["pairing"] = {
            "enabled": True,
            "pairing_only": True,
            "extensions": ".lrc .kar",
        }

        for filename in ["track_1.kar", "track_1.lrc", "track_1.jpg"]:
            env.create_file(album_path / filename)

        env.run_cli_command("import")

        env.assert_in_import_dir("the_album/track_1.lrc")
        env.assert_in_import_dir("the_album/artifact.lrc")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.kar")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/track_1.jpg")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_pairing_extensions_are_additive_to_toplevel_extensions(self) -> None:
        """Ensure that those extensions defined in pairing extend any extensions
        defined in the `extensions` config.
        """
        env = self.env

        album_path = env.create_flat_import_dir(
            media_files=[MediaSetup(count=2, generate_pair=False)]
        )
        env.setup_import_session(autotag=False)

        env.config["filetote"]["extensions"] = ".jpg"
        env.config["filetote"]["pairing"] = {
            "enabled": True,
            "extensions": ".lrc",
        }

        for filename in ["track_1.kar", "track_1.lrc", "track_1.jpg"]:
            env.create_file(album_path / filename)

        env.run_cli_command("import")

        env.assert_in_import_dir("the_album/track_1.lrc")
        env.assert_in_import_dir("the_album/artifact.lrc")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/track_1.jpg")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/track_1.kar")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")
