"""Media file creation and management for beets plugin tests."""

import logging
import shutil

from dataclasses import asdict, dataclass
from pathlib import Path

from mediafile import MediaFile

from ._item_model import MediaMeta
from .utils import RSRC, BeetsTestUtils

log = logging.getLogger("beets")


@dataclass
class MediaSetup:
    """Configuration for media files to create in an import directory."""

    file_type: str = "mp3"
    count: int = 3
    generate_pair: bool = True
    pair_subfolders: bool = False


class MediaCreator(BeetsTestUtils):
    """Mixin providing media file creation and update methods."""

    def create_medium(
        self, path: Path, media_meta: MediaMeta | None = None
    ) -> MediaFile:
        """Create a media file at ``path`` with the given metadata."""
        if media_meta is None:
            media_meta = MediaMeta()

        path.parent.mkdir(parents=True, exist_ok=True)

        resource_name = self.get_rsrc_from_extension(path.suffix)
        resource_path = RSRC / resource_name

        shutil.copy(resource_path, path)
        medium = MediaFile(str(path))

        for item, value in asdict(media_meta).items():
            setattr(medium, item, value)
        medium.save()
        return medium

    def update_medium(self, path: Path, meta_updates: dict[str, str]) -> None:
        """Update metadata on an existing media file."""
        medium = MediaFile(str(path))
        for item, value in meta_updates.items():
            setattr(medium, item, value)
        medium.save()

    def generate_paired_media_list(  # noqa: PLR0913
        self,
        album_path: Path,
        count: int = 3,
        generate_pair: bool = True,
        pair_subfolders: bool = False,
        filename_prefix: str = "track_",
        file_type: str = "mp3",
        title_prefix: str = "Tag Title ",
        disc: int = 1,
        disctotal: int = 1,
    ) -> list[MediaFile]:
        """Generate the desired number of media files with optional paired .lrc
        files.
        """
        media_list: list[MediaFile] = []

        while count > 0:
            trackname = f"{filename_prefix}{count}"
            media_path = album_path / f"{trackname}.{file_type}"

            media_list.append(
                self.create_medium(
                    path=media_path,
                    media_meta=MediaMeta(
                        title=f"{title_prefix}{count}",
                        track=count,
                        disc=disc,
                        disctotal=disctotal,
                    ),
                )
            )
            count -= 1

            if generate_pair:
                pair_path: Path = album_path
                if pair_subfolders:
                    pair_path = album_path / "lyrics" / "lyric-subfolder"
                pair_path.mkdir(parents=True, exist_ok=True)
                self.create_file(pair_path / f"{trackname}.lrc")

        return media_list
