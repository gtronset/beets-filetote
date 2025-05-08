"""Tests that the version specified for the plugin matches the value in pyproject."""

from typing import List, Optional

import beetsplug
import toml  # type: ignore

from tests.helper import FiletoteTestCase


class FiletoteVersionTest(FiletoteTestCase):
    """Tests that the version specified for the plugin matches the value in
    pyproject.
    """

    def setUp(self, _other_plugins: Optional[List[str]] = None) -> None:
        """Provides shared setup for tests."""
        super().setUp()

    def test_version_matches(self) -> None:
        """Ensure that the Filetote version is properly reflected in the right
        areas.
        """
        plugin_version = beetsplug.__version__

        with open("./pyproject.toml", encoding="utf-8") as pyproject_file:
            data = toml.load(pyproject_file)

            toml_version = data["tool"]["poetry"]["version"]

            assert plugin_version == toml_version
