from typing import Any

class Template:
    def __init__(self, default: object = ...): ...

class OneOf(Template):
    def __init__(self, allowed: list[Any], default: object = ...): ...

class StrSeq(Template):
    def __init__(self, split: bool = ..., default: object = ...): ...
