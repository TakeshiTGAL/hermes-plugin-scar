"""Stop a denied command shape, and record a deny from the approval card.

pre_tool_call blocks only a call to a tool that has a stored scar, and it reads
only the argument keys that scar kept. A call to any other tool is not read.
post_approval_response only observes. A choice other than deny does not write
a scar. The numbered menu submits the choice id deny when the person selects
that row. This plugin does not read the letters never.

scar_forget asks for the Hermes approval card through the public approve
directive. Each call gets a new rule key, so always does not cover the next forget.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import textwrap

from . import clock, gates, ledger
from .redact import redact
from .shape import ShapeError, call_shape

OWN = frozenset({"scar_check", "scar_list"})
FORGET = "scar_forget"
# Every scar this plugin writes is a terminal scar: the approval card hands the
# hook a shell command. A ledger that cannot be read can only be guarding these.
CARD_TOOLS = frozenset({"terminal"})
UNREADABLE = (
    "BLOCKED: the scar ledger could not be read, so this rm command was not run. "
    "Other commands still run. A person can move plugin-data/scar/ledger.json "
    "aside in the Hermes home to start a new ledger."
)
UNCOMPARED = "BLOCKED: this call could not be compared with the scar ledger, so it was not run."
FORGET_ABSENT = (
    "BLOCKED: scar_forget does not run in cron, a single query, a webhook, "
    "an api_server session, or a plugin host, including after always, "
    "so this scar was not forgotten."
)
# Hermes v0.22.2 `hermes chat --cli` shows this message as the approval
# description. The fallback terminal is 100 by 24. The command line is the
# short plugin label, and the menu is once, session, always, and deny, so 7
# description lines remain. The panel wraps that description at 63 columns
# and replaces anything longer with a truncation marker. A question past
# that budget is not sent.
_CARD_WIDTH = 63
_CARD_LINES = 7
FORGET_CUT = (
    "BLOCKED: the forget question does not fit on the approval card, "
    "so this scar was not forgotten."
)
# Approval cards that are not a shell command. A deny there is not an rm shape.
_NOT_SHELL = ("plugin_rule:", "cua:", "ssh_config_write")


def _block(message: str) -> dict:
    return {"action": "block", "message": message}


def _card_line_count(message: str) -> int:
    """Lines the v0.22.2 CLI approval description would use at 63 columns."""
    lines: list[str] = []
    for part in message.splitlines() or [""]:
        wrapped = textwrap.wrap(
            part,
            width=_CARD_WIDTH,
            replace_whitespace=False,
            drop_whitespace=False,
        )
        lines.extend(wrapped or [""])
    return len(lines)


def forget_rule_key(row: dict) -> str:
    """A new approval key on every call. A saved always line does not match the next forget."""
    nonce = secrets.token_hex(8)
    body = json.dumps(
        {
            "id": row["id"],
            "recorded_at": row["recorded_at"],
            "tool": row["tool"],
            "arg_keys": row["arg_keys"],
            "danger_tokens": row["danger_tokens"],
            "preview": row["preview"],
            "call": nonce,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return FORGET + ":" + hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def _person_absent() -> bool:
    return gates.unattended() or gates.in_plugin_host_process()


def _forget_directive(args: object) -> dict | None:
    """Ask the person before a scar is forgotten. A missing scar needs no card.

    Hermes honors a permanent allowlist before it applies the cron deny, so an
    unattended call is blocked here and never reaches that gate.
    """
    if not isinstance(args, dict) or set(args) != {"id"}:
        return None
    ident = args.get("id")
    if isinstance(ident, bool) or not isinstance(ident, int):
        return None
    view = ledger.load()
    if view.status != "ok":
        return None
    row = next((item for item in view.doc["scars"] if item["id"] == ident), None)
    if row is None:
        return None
    if _person_absent():
        return _block(FORGET_ABSENT)
    message = (
        f"Forget {clock.receipt(row['id'], row['recorded_at'])} "
        f"({row['tool']}: {' '.join(row['danger_tokens'])}; {row['preview']}). "
        "After this, that shape is no longer stopped."
    )
    if _card_line_count(message) > _CARD_LINES:
        return _block(FORGET_CUT)
    return {"action": "approve", "message": message, "rule_key": forget_rule_key(row)}


def _unreadable_directive(tool_name: str, args: object) -> dict | None:
    """A broken ledger stops only an rm command on a tool the card can scar."""
    if tool_name not in CARD_TOOLS:
        return None
    try:
        shape = call_shape(tool_name, args)
    except ShapeError:
        # The shape was not read, so this call is not an rm command.
        return None
    return _block(UNREADABLE) if shape["danger_tokens"] else None


def on_pre_tool_call(tool_name: str = "", args: object = None, **kwargs: object) -> dict | None:
    """Block a call that a stored scar covers. Only the tool and keys a scar kept are read."""
    kwargs.pop("recorded_at", None)
    if tool_name in OWN:
        return None
    try:
        if tool_name == FORGET:
            return _forget_directive(args)
        try:
            view = ledger.load()
        except Exception:
            return _unreadable_directive(tool_name, args)
        if view.status == "unreadable":
            return _unreadable_directive(tool_name, args)
        if view.status != "ok":
            return None
        scars = [row for row in view.doc["scars"] if row["tool"] == tool_name]
        if not scars:
            return None
        keys = {key for row in scars for key in row["arg_keys"]}
        try:
            shape = call_shape(tool_name, args, keys=keys)
        except ShapeError:
            return _block(UNCOMPARED)
        match = ledger.lowest_match({"scars": scars}, shape)
        if match is None:
            return None
        return _block(clock.receipt_line(match["id"], match["recorded_at"]))
    except Exception:
        if tool_name == FORGET:
            return _block("BLOCKED: scar_forget could not ask for approval, so nothing was forgotten.")
        return _unreadable_directive(tool_name, args)


def on_post_approval_response(choice: str = "", command: str = "", **kwargs: object) -> None:
    """When the person denied an rm command, keep that shape. Other choices do not."""
    kwargs.pop("recorded_at", None)
    try:
        if gates.unattended() or gates.in_plugin_host_process():
            return None
        if choice != "deny":
            return None
        pattern_key = kwargs.get("pattern_key")
        if isinstance(pattern_key, str) and pattern_key.startswith(_NOT_SHELL):
            return None
        if not isinstance(command, str) or not command.strip():
            return None
        if ledger.load().status == "unreadable":
            return None
        try:
            shape = call_shape("terminal", {"command": command})
        except ShapeError:
            return None
        if not shape["danger_tokens"]:
            return None
        preview = redact(command)
        ledger.add_scar(shape, preview)
    except Exception:
        return None
    return None
