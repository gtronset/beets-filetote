"""Tests nested directories for the beets-filetote plugin."""

from tests.helper import FiletoteTestCase


class FiletoteFromNestedDirectoryTest(FiletoteTestCase):
    """
    Tests to check that Filetote copies or moves artifact files from a nested directory
    structure. i.e. songs in an album are imported from two directories corresponding to
    disc numbers or flat option is used
    """
