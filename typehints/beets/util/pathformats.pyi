from typing import Any, TypeAlias

from beets.util.functemplate import Template

PathFormat: TypeAlias = tuple[str, Template]

def get_path_formats(subview: Any) -> list[PathFormat]: ...
