"""Response models must survive fields the API adds after this SDK shipped.

The API adds response fields without a version bump. An SDK that raises on a
key it does not know breaks every customer on the day the field ships, so:

- every response model, built from API JSON, ignores keys it does not
  declare, at every level of nesting, and keeps every key it does declare;
- the clients build response models only through that path.

Both properties are driven over every model in `euromail.types`, so a model
added later is covered without touching this file.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import types
import typing
from pathlib import Path
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

import pytest

import euromail
from euromail import types as models
from euromail.types import from_dict

UNKNOWN = "field_from_a_newer_api"

# Built by the clients from the pagination block, not from a response object.
BUILT_FROM_PARTS = {"PaginatedResponse"}


def _response_models() -> list[type]:
    # Request types serialise themselves with `to_dict`; everything else is
    # something the API sends back.
    return [
        cls
        for _, cls in inspect.getmembers(models, inspect.isclass)
        if cls.__module__ == models.__name__
        and dataclasses.is_dataclass(cls)
        and not hasattr(cls, "to_dict")
    ]


def _sample(hint: Any) -> tuple[Any, Any]:
    """Return (payload as the API would send it with an unknown key added at
    every object level, the same payload without those keys)."""
    if isinstance(hint, type) and dataclasses.is_dataclass(hint):
        hints = get_type_hints(hint)
        sent, kept = {UNKNOWN: "ignored"}, {}
        for f in dataclasses.fields(hint):
            sent[f.name], kept[f.name] = _sample(hints[f.name])
        return sent, kept
    origin = get_origin(hint)
    if origin is list:
        sent, kept = _sample(get_args(hint)[0] if get_args(hint) else str)
        return [sent], [kept]
    if origin is dict:
        sent, kept = _sample(get_args(hint)[1] if get_args(hint) else str)
        return {"key": sent}, {"key": kept}
    if origin is Union or origin is types.UnionType:
        return _sample(next(a for a in get_args(hint) if a is not type(None)))
    if origin is Literal:
        return get_args(hint)[0], get_args(hint)[0]
    if isinstance(hint, typing.TypeVar) or hint is Any:
        return {"opaque": [1]}, {"opaque": [1]}
    value = {str: "s", int: 7, float: 0.5, bool: True}[hint]
    return value, value


@pytest.mark.parametrize("cls", _response_models(), ids=lambda c: c.__name__)
def test_response_model_ignores_unknown_fields_and_keeps_known_ones(cls):
    sent, kept = _sample(cls)

    built = from_dict(cls, sent)

    assert isinstance(built, cls)
    assert dataclasses.asdict(built) == kept


def test_clients_build_response_models_only_through_from_dict():
    names = {cls.__name__ for cls in _response_models()} - BUILT_FROM_PARTS
    package = Path(euromail.__file__).parent
    direct = []
    for module in ("client.py", "async_client.py"):
        tree = ast.parse((package / module).read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in names
            ):
                direct.append(f"{module}:{node.lineno} {node.func.id}(...)")
    assert direct == [], "build these with from_dict(Model, data): " + ", ".join(direct)
