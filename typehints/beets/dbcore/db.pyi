from __future__ import annotations

from typing import Any, Iterator, List, Literal, Mapping, Union

ALL_KEYS: Literal["*"] = "*"

class Model:
    def keys(self, computed: bool = False) -> Union[Literal["*"], List[str]]: ...
    def _get(self, key: str, default: Any = None, raise_: bool = False) -> Any: ...

    get = _get

    def _setitem(self, key: str, value: str) -> bool: ...
    def __setitem__(self, key: str, value: str) -> None:
        self._setitem(key, value)

    def _type(self, key: str) -> str: ...
    def formatted(
        self,
        included_keys: Union[Literal["*"], List[str]] = ALL_KEYS,
        for_path: bool = False,
    ) -> FormattedMapping: ...

class FormattedMapping(Mapping[str, str]):
    def __init__(
        self,
        model: Model,
        included_keys: Union[Literal["*"], List[str]] = ALL_KEYS,
        for_path: bool = False,
    ):
        self.for_path = for_path
        self.model = model
        if included_keys == ALL_KEYS:
            # Performance note: this triggers a database query.
            self.model_keys = self.model.keys(True)
        else:
            self.model_keys = included_keys

    def __getitem__(self, key: str) -> str: ...
    def __iter__(self) -> Iterator[str]: ...
    def __len__(self) -> int: ...
