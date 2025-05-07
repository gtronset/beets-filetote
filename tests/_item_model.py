"""Item Model for Filetote tests."""

from dataclasses import dataclass


@dataclass
class MediaMeta:
    """
    Metadata for created media files.
    Follows typing from the [Beets Item](https://github.com/beetbox/beets/blob/9527a07767629c1ceb99c2cd681b78172a7272a0/beets/library.py#L475-L563)
    """

    title: str = "Tag Title 1"
    artist: str = "Tag Artist"
    albumartist: str = "Tag Album Artist"
    album: str = "Tag Album"
    genre: str = "Tag genre"
    lyricist: str = "Tag lyricist"
    composer: str = "Tag composer"
    arranger: str = "Tag arranger"
    grouping: str = "Tag grouping"
    work: str = "Tag work title"
    mb_workid: str = "Tag work musicbrainz id"
    work_disambig: str = "Tag work disambiguation"
    year: int = 2023
    month: int = 2
    day: int = 3
    track: int = 1
    tracktotal: int = 5
    disc: int = 1
    disctotal: int = 7
    lyrics: str = "Tag lyrics"
    comments: str = "Tag comments"
    bpm: int = 8
    comp: bool = True
    mb_trackid: str = "someID-1"
    mb_albumid: str = "someID-2"
    mb_artistid: str = "someID-3"
    mb_albumartistid: str = "someID-4"
    mb_releasetrackid: str = "someID-5"
