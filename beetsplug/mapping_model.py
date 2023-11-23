""" "Mapping" Model for Filetote. """

from sys import version_info
from typing import Dict, List, Optional, Union

from beets.dbcore import db
from beets.dbcore import types as db_types

if version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal  # type: ignore # pylint: disable=import-error


class FiletoteMappingModel(db.Model):
    """Model for a FiletoteMappingFormatted."""

    _fields = {
        "albumpath": db_types.STRING,
        "medianame_old": db_types.STRING,
        "medianame_new": db_types.STRING,
        "old_filename": db_types.STRING,
    }

    def set(self, key: str, value: str) -> None:
        """Get the formatted version of model[key] as string."""
        super().__setitem__(key, value)

    @classmethod
    def _getters(cls) -> Dict[None, None]:
        """Return "blank" for getter functions."""
        return {}

    def _template_funcs(self) -> Dict[None, None]:
        """Return "blank" for template functions."""
        return {}


class FiletoteMappingFormatted(db.FormattedMapping):
    """
    Formatted Mapping that does not replace path separators for certain keys
    (e.g., albumpath).
    """

    ALL_KEYS: Literal["*"] = "*"

    def __init__(
        self,
        model: FiletoteMappingModel,
        included_keys: Union[Literal["*"], List[str]] = ALL_KEYS,
        for_path: bool = False,
        whitelist_replace: Optional[List[str]] = None,
    ):
        super().__init__(model, included_keys, for_path)
        if whitelist_replace is None:
            whitelist_replace = []
        self.whitelist_replace = whitelist_replace

    def __getitem__(self, key: str) -> str:
        """
        Get the formatted version of model[key] as string. Any value
        provided in the `whitelist_replace` list will not have the path
        separator replaced.
        """
        if key in self.whitelist_replace:
            value = self.model._type(key).format(self.model.get(key))
            if isinstance(value, bytes):
                value = value.decode("utf-8", "ignore")
            return str(value)
        return str(super().__getitem__(key))
