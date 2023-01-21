""" Dataclasses for Filetote representing Settings/Config-related content along with
data used in processing extra files/artifacts. """

from dataclasses import dataclass
from sys import version_info
from typing import Any, List, Optional, Union

from beets.util import MoveOperation

from .mapping_model import FiletoteMappingModel

if version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal  # type: ignore # pylint: disable=import-error


@dataclass
class FiletoteArtifact:
    """An individual FileTote Artifact item for processing."""

    path: str
    paired: bool


@dataclass
class FiletoteArtifactCollection:
    """An individual FileTote Item collection for processing."""

    artifacts: List[FiletoteArtifact]
    mapping: FiletoteMappingModel
    source_path: str


@dataclass
class FiletoteSessionData:
    """Configuration settings for FileTote Item."""

    operation: Optional[MoveOperation] = None
    beets_lib = None
    import_path: Optional[bytes] = None

    def adjust(self, attr: str, value: Any) -> None:
        """Adjust provided attribute of class with provided value."""
        setattr(self, attr, value)


@dataclass
class FiletoteConfig:
    """Configuration settings for FileTote Item."""

    session: Union[FiletoteSessionData, None] = None
    extensions: Union[Literal[".*"], list] = ".*"
    filenames: Union[Literal[""], list] = ""
    exclude: Union[Literal[""], list] = ""
    print_ignored: bool = False
    pairing: bool = False
    pairing_only: bool = False

    # def __post_init__(self):
    #    self.session = FiletoteSessionData()
