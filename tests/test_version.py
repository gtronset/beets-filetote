"""
Tests that the version specified for the plugin matches the value in pyproject.
"""

from typing import List, Optional

import toml  # type: ignore # pylint: disable=import-error

import beetsplug
from tests.helper import FiletoteTestCase


class FiletoteVersionTest(FiletoteTestCase):
    """
    Tests that the version specified for the plugin matches the value in
    pyproject.
    """

    def setUp(self, other_plugins: Optional[List[str]] = None) -> None:
        """Provides shared setup for tests."""
        super().setUp()

    def test_version_matches(self) -> None:
        """Ensure that the Filetote version is properly reflected in the right
        areas."""

        plugin_version = beetsplug.__version__

        with open("./pyproject.toml", "r", encoding="utf-8") as pyproject_file:
            data = toml.load(pyproject_file)

            toml_version = data["tool"]["poetry"]["version"]

            self.assertions.assertEqual(plugin_version, toml_version)
