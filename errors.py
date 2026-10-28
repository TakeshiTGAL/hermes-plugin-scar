"""Tool results. A failure names its kind and the next step."""

from __future__ import annotations

NEXT = {
    "bad_argument": "Fix the named field and call again. Nothing was written.",
    "ledger_unreadable": "The ledger file is present but could not be parsed. Leave it in place. Nothing was written.",
    "ledger_full": "The ledger is at its cap. Nothing was written.",
    "shape_invalid": "Pass a plain tool name and a smaller argument object. Nothing was written.",
    "not_found": "Call scar_list for the ids that exist. Nothing was written.",
    "unattended": "A person has to forget a scar from an interactive session. Nothing was written.",
    "internal": "Retry once. If it repeats, say the tool failed.",
}


def failure(kind: str, message: str, next_step: str | None = None, **extra: object) -> dict:
    body: dict = {
        "ok": False,
        "error_type": kind,
        "error": message,
        "next_step": NEXT[kind] if next_step is None else next_step,
    }
    body.update(extra)
    return body


def success(**payload: object) -> dict:
    body: dict = {"ok": True}
    body.update(payload)
    return body
