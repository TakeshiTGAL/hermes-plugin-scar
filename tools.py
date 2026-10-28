"""Tool handlers. They return JSON text and do not raise."""

from __future__ import annotations

import json
from typing import Any, Callable

from .errors import failure, success
from . import gates
from .ledger import LedgerProblem, load, lowest_match, public_scar, remove_scar
from .shape import ShapeError, call_shape

_FIELDS = {
    "scar_check": frozenset({"tool", "arguments"}),
    "scar_list": frozenset(),
    "scar_forget": frozenset({"id"}),
}
ABSENT = "The ledger file is absent."
NONE = "The ledger was read and no scar covers this call."
EMPTY = "The ledger was read and it holds no scars."


def _holds(count: int) -> str:
    word = "scar" if count == 1 else "scars"
    return f"The ledger was read and it holds {count} {word}."


def _dump(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def _wrap(fn: Callable[..., dict]) -> Callable:
    def handler(args: dict | None = None, session_id: str = "", task_id: str = "", **_kwargs: Any) -> str:
        try:
            return _dump(fn(dict(args or {})))
        except LedgerProblem as exc:
            return _dump(exc.as_failure())
        except Exception:
            return _dump(failure("internal", "The tool failed before it finished."))

    return handler


def _reject(name: str, args: dict) -> dict | None:
    if not isinstance(args, dict):
        return failure("bad_argument", "Arguments must be an object.", field="arguments")
    allowed = _FIELDS[name]
    extra = sorted(set(args) - allowed)
    if extra:
        return failure("bad_argument", f"{extra[0]} is not accepted.", field=extra[0])
    for field in sorted(allowed):
        if field not in args:
            return failure("bad_argument", f"{field} is required.", field=field)
    return None


def _view_or_error():
    view = load()
    if view.status == "unreadable":
        return failure(
            "ledger_unreadable",
            "The ledger file is present but could not be parsed. Leave it in place.",
        )
    return view


def _check(args: dict) -> dict:
    rejected = _reject("scar_check", args)
    if rejected is not None:
        return rejected
    view = _view_or_error()
    if isinstance(view, dict):
        return view
    if view.status == "absent":
        return success(status="absent", message=ABSENT, covered=False)
    try:
        shape = call_shape(args["tool"], args["arguments"])
    except ShapeError:
        return failure("shape_invalid", "The tool name or the arguments cannot be compared.")
    match = lowest_match(view.doc, shape)
    if match is None:
        return success(status="read", message=NONE, covered=False, scars=len(view.doc["scars"]))
    shown = public_scar(match)
    return success(status="read", message=shown["receipt"], covered=True, scar=shown)


def _list(args: dict) -> dict:
    rejected = _reject("scar_list", args)
    if rejected is not None:
        return rejected
    view = _view_or_error()
    if isinstance(view, dict):
        return view
    if view.status == "absent":
        return success(status="absent", message=ABSENT, scars=[])
    rows = [public_scar(row) for row in view.doc["scars"]]
    if not rows:
        return success(status="read", message=EMPTY, scars=[])
    return success(status="read", message=_holds(len(rows)), scars=rows)


def _forget(args: dict) -> dict:
    """Remove one scar. Hermes asked the person in pre_tool_call before this runs.

    An unattended session never removes a scar, even when Hermes would skip the
    card because of yolo, approvals off, or a permanent allowlist entry.
    """
    rejected = _reject("scar_forget", args)
    if rejected is not None:
        return rejected
    ident = args["id"]
    if isinstance(ident, bool) or not isinstance(ident, int) or ident < 1:
        return failure("bad_argument", "id must be a whole number from scar_list.", field="id")
    if gates.unattended() or gates.in_plugin_host_process():
        view = _view_or_error()
        if isinstance(view, dict):
            return view
        if view.status == "absent":
            return failure("not_found", "The ledger file is absent, so there is no scar to forget.")
        if not any(item["id"] == ident for item in view.doc["scars"]):
            return failure("not_found", f"No scar has id {ident}.")
        return failure(
            "unattended",
            "scar_forget does not run in cron, a single query, a webhook, an api_server session, or a plugin host.",
        )
    view = _view_or_error()
    if isinstance(view, dict):
        return view
    if view.status == "absent":
        return failure("not_found", "The ledger file is absent, so there is no scar to forget.")
    removed = remove_scar(ident)
    if removed is None:
        return failure("not_found", f"No scar has id {ident}.")
    row, left = removed
    return success(
        status="forgotten",
        message=f"Forgot scar #{ident}. A matching call is no longer stopped by it. {_holds(left)}",
        forgotten=public_scar(row),
    )


HANDLERS = {
    "scar_check": _wrap(_check),
    "scar_list": _wrap(_list),
    "scar_forget": _wrap(_forget),
}
