"""Lightweight stub of the upstream inline plugin for test usage.

The real plugin compiles Python expressions defined in the Beets config and
exposes them as template fields. The tests only need the ability to define
``item_fields`` (and, by extension, ``album_fields``) expressions, so this
stub evaluates those expressions in a minimal, sandboxed fashion.
"""

from __future__ import annotations

from typing import Any, Callable, cast

from beets import config
from beets.plugins import BeetsPlugin

_SAFE_GLOBALS: dict[str, object] = {
    "__builtins__": {},
}


def _field_expressions(view: Any, *, target: str) -> dict[str, str]:
    """Pull string expressions from a ConfigView safely."""
    del target  # only needed for API parity with the real plugin

    config_view = cast("Any", view)

    if not config_view.exists():
        return {}

    expressions = config_view.get(dict)
    if expressions is None:
        return {}

    return {str(key): str(value) for key, value in expressions.items()}


def _evaluate_expression(expression: str, context: dict[str, object]) -> object:
    """Evaluate the inline expression using a restricted environment."""
    code = compile(expression, "<inline>", "eval")
    return eval(code, _SAFE_GLOBALS, context)


def _context_from_obj(obj: object) -> dict[str, Any]:
    """Build an evaluation context for a Beets Item/Album-like object."""
    context: dict[str, Any]
    if hasattr(obj, "keys") and hasattr(obj, "get"):
        keys_method = obj.keys
        getter = obj.get
        context = {key: getter(key) for key in keys_method()}
    else:
        context = obj.__dict__.copy()

    context["obj"] = obj
    return context


class InlinePlugin(BeetsPlugin):
    """Minimal stand-in for the upstream inline plugin."""

    @property
    def template_fields(self) -> dict[str, Callable[[object], Any]]:
        """Return inline item template functions."""
        expressions = _field_expressions(config["item_fields"], target="item")

        def make_func(expr: str) -> Callable[[object], Any]:
            def _func(item: object) -> Any:
                return _evaluate_expression(expr, _context_from_obj(item))

            return _func

        return {name: make_func(expr) for name, expr in expressions.items()}

    @property
    def album_template_fields(self) -> dict[str, Callable[[object], Any]]:
        """Return inline album template functions."""
        expressions = _field_expressions(config["album_fields"], target="album")

        def make_func(expr: str) -> Callable[[object], Any]:
            def _func(album: object) -> Any:
                return _evaluate_expression(expr, _context_from_obj(album))

            return _func

        return {name: make_func(expr) for name, expr in expressions.items()}
