import os
import sys

from beets import config

from tests.helper import CopyFileArtifactsTestCase


class CopyFileArtifactsFromNestedDirectoryTest(CopyFileArtifactsTestCase):
    """
    Tests to check that copyfileartifacts copies or moves artifact files from a nested directory
    structure. i.e. songs in an album are imported from two directories corresponding to
    disc numbers or flat option is used
    """
