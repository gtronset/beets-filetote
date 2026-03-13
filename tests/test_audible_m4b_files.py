"""Tests that m4b music/audiobook files are ignored for the beets-filetote
plugin, when the beets-audible plugin is loaded.
"""

from tests.pytest_beets_plugin import MediaSetup
from tests.pytest_beets_plugin.fixtures import BeetsEnvFactory


# TODO(gtronset): mediafile.TYPES only contains a subset of formats that MediaFile/
# Mutagen can actually read. These additional types are known to be importable by
# beets (via Mutagen's MP4, ASF, and WAV handlers) but are absent from
# the TYPES dict. Without these, Filetote would incorrectly treat them as
# artifacts.
#
# See: https://github.com/beetbox/mediafile/blob/master/mediafile/constants.py
# See: https://mutagen.readthedocs.io/en/latest/api/mp4.html
# _ADDITIONAL_MEDIA_TYPES: dict[str, str] = {
#     # Mutagen MP4 container variants (not in mediafile.TYPES)
#     "m4a": "AAC",
#     "m4b": "AAC Audiobook",
#     "m4v": "M4V",
#     "mp4": "MP4",
#     # Mutagen ASF/WMA (mediafile.TYPES lists "asf" but not "wma")
#     "wma": "Windows Media",
#     # Alternate WAV extension (mediafile.TYPES lists "wav" but not "wave")
#     "wave": "WAVE",
# }
# ...
# # File types handled by beets, used to check if a file is an artifact.
# # Combine mediafile.TYPES with known additional Mutagen-supported formats.
# self._beets_file_types: dict[str, str] = {
#     **BEETS_FILE_TYPES,
#     **_ADDITIONAL_MEDIA_TYPES,
# }
# --END
# https://github.com/gtronset/beets-filetote/pull/275
class TestM4BFilesIgnored:
    """Tests to check that Filetote does not copy music/audiobook files when the
    beets-audible plugin is present.

    Without the audible plugin, ``m4b`` is not in ``mediafile.TYPES``, so
    Filetote treats it as an artifact and copies it using its source filename.
    When audible is loaded, Filetote adds ``m4b`` to its internal file type
    list and skips it, letting beets handle the import normally.
    """

    def test_m4b_not_copied_as_artifact_with_audible(
        self, beets_flat_env: BeetsEnvFactory
    ) -> None:
        """With audible loaded, Filetote recognizes ``.m4b`` as a music file
        type and does NOT copy it as an artifact.
        """
        env = beets_flat_env(
            media_files=[
                MediaSetup(file_type="mp3", count=1),
                MediaSetup(file_type="m4b", count=1, generate_pair=False),
            ]
        )
        env.plugins = ["audible"]
        env.config["filetote"]["extensions"] = ".*"

        env.run_cli_command("import")

        env.assert_in_import_dir("the_album/track_1.mp3")
        env.assert_in_import_dir("the_album/track_1.m4b")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.mp3")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.m4b")

        # Filetote should NOT copy m4b as an artifact (source-named)
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/track_1.m4b")

    def test_m4b_copied_as_artifact_without_audible(
        self, beets_flat_env: BeetsEnvFactory
    ) -> None:
        """Without audible, ``m4b`` is NOT in Filetote's file type list, so
        Filetote treats it as an artifact and copies it with its source
        filename.

        Note: beets also imports it as media (MediaFile can read m4b via
        Mutagen's MP4 handler), so both the artifact copy AND the media
        import exist in the library.
        """
        env = beets_flat_env(
            media_files=[
                MediaSetup(file_type="mp3", count=1),
                MediaSetup(file_type="m4b", count=1, generate_pair=False),
            ]
        )
        env.config["filetote"]["extensions"] = ".*"

        env.run_cli_command("import")

        # Without audible, Filetote copies m4b as an artifact
        env.assert_in_lib_dir("Tag Artist/Tag Album/track_1.m4b")

        # beets ALSO imports it as media
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.m4b")
