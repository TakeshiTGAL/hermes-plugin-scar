"""The scar ledger. A missing file was looked for. A broken file is not called empty."""

from __future__ import annotations

import json
import threading

from . import clock
from .errors import NEXT, failure
from .redact import redact
from .safe_write import WriteRefused, write_bytes
from .shape import ALLOWED_TOKENS, KEY_RE, TOOL_RE
from .storage import StorageError, plugin_root

LEDGER_NAME = "ledger.json"
VERSION = 2
SCAR_MAX = 200
FILE_MAX = 800000
_SCAR_KEYS = frozenset(
    {"id", "decision", "recorded_at", "tool", "arg_keys", "danger_tokens", "preview"}
)
_LOCK = threading.Lock()


class LedgerProblem(Exception):
    def __init__(self, kind: str, message: str):
        self.kind = kind
        self.message = message
        super().__init__(message)

    def as_failure(self) -> dict:
        return failure(self.kind, self.message, NEXT[self.kind])


class LedgerView:
    def __init__(self, status: str, doc: dict | None = None, reason: str = ""):
        self.status = status
        self.doc = doc
        self.reason = reason


def _blank() -> dict:
    return {"scar_ledger_version": VERSION, "scars": []}


def _string_list(value: object, *, allow: frozenset[str] | None, empty_ok: bool) -> bool:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        return False
    if value != sorted(set(value)):
        return False
    if not empty_ok and not value:
        return False
    if allow is not None and any(item not in allow for item in value):
        return False
    if any(KEY_RE.fullmatch(item) is None for item in value):
        return False
    return True


def _scar_ok(row: object) -> bool:
    if not isinstance(row, dict) or set(row) != _SCAR_KEYS:
        return False
    ident = row.get("id")
    if isinstance(ident, bool) or not isinstance(ident, int) or ident < 1:
        return False
    if row.get("decision") != "deny":
        return False
    try:
        clock.parse_when(row.get("recorded_at"))
    except (TypeError, ValueError):
        return False
    tool = row.get("tool")
    if not isinstance(tool, str) or TOOL_RE.fullmatch(tool) is None:
        return False
    if not _string_list(row.get("arg_keys"), allow=None, empty_ok=False):
        return False
    if not _string_list(row.get("danger_tokens"), allow=ALLOWED_TOKENS, empty_ok=False):
        return False
    preview = row.get("preview")
    if not isinstance(preview, str) or len(preview) > 500:
        return False
    return True


def _valid(doc: object) -> bool:
    if not isinstance(doc, dict) or set(doc) != {"scar_ledger_version", "scars"}:
        return False
    version = doc.get("scar_ledger_version")
    if isinstance(version, bool) or version != VERSION:
        return False
    scars = doc.get("scars")
    if not isinstance(scars, list) or len(scars) > SCAR_MAX:
        return False
    seen: set[int] = set()
    for row in scars:
        if not _scar_ok(row):
            return False
        ident = row["id"]
        if ident in seen:
            return False
        seen.add(ident)
    return True


def _path():
    root = plugin_root()
    return root, root / LEDGER_NAME


def load() -> LedgerView:
    """Read the ledger. This does not create the file."""
    try:
        _root, path = _path()
    except StorageError as exc:
        return LedgerView("unreadable", reason=exc.error)
    try:
        if path.is_symlink():
            return LedgerView("unreadable", reason="symlink")
        if not path.exists():
            return LedgerView("absent")
        raw = path.read_bytes()
    except OSError as exc:
        return LedgerView("unreadable", reason=exc.__class__.__name__)
    if len(raw) > FILE_MAX:
        return LedgerView("unreadable", reason="size")
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return LedgerView("unreadable", reason="json")
    if not _valid(doc):
        return LedgerView("unreadable", reason="schema")
    return LedgerView("ok", doc)


def covers(scar: dict, shape: dict) -> bool:
    """True when the scar's tool, keys, and tokens are all present on the call."""
    if scar["tool"] != shape["tool"]:
        return False
    if not set(scar["arg_keys"]).issubset(shape["arg_keys"]):
        return False
    tokens = scar["danger_tokens"]
    if not tokens:
        return False
    return set(tokens).issubset(shape["danger_tokens"])


def lowest_match(doc: dict, shape: dict) -> dict | None:
    matches = [row for row in doc["scars"] if covers(row, shape)]
    if not matches:
        return None
    return min(matches, key=lambda row: row["id"])


def public_scar(row: dict) -> dict:
    """The stored row plus a receipt computed from the id and the clock."""
    return {
        "id": row["id"],
        "decision": row["decision"],
        "recorded_at": row["recorded_at"],
        "tool": row["tool"],
        "arg_keys": list(row["arg_keys"]),
        "danger_tokens": list(row["danger_tokens"]),
        "preview": redact(row["preview"]),
        "receipt": clock.receipt(row["id"], row["recorded_at"]),
    }


def _same(row: dict, shape: dict) -> bool:
    return (
        row["tool"] == shape["tool"]
        and row["arg_keys"] == shape["arg_keys"]
        and row["danger_tokens"] == shape["danger_tokens"]
    )


def _write(doc: dict) -> None:
    data = (json.dumps(doc, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if len(data) > FILE_MAX:
        raise LedgerProblem("ledger_full", "The ledger is at its cap. Nothing was written.")
    if not _valid(json.loads(data.decode("utf-8"))):
        raise LedgerProblem("shape_invalid", "The shape cannot be stored. Nothing was written.")
    try:
        root = plugin_root()
    except StorageError as exc:
        raise LedgerProblem("ledger_unreadable", exc.error) from exc
    try:
        write_bytes(root, LEDGER_NAME, data, create=True, exclusive=False, cut_hardlink=True)
    except WriteRefused as exc:
        raise LedgerProblem("ledger_unreadable", "The ledger could not be written. Nothing was replaced.") from exc


def add_scar(shape: dict, preview: str) -> dict:
    """Store one deny. The clock is read here. An empty token set is refused."""
    if not isinstance(preview, str):
        raise LedgerProblem("shape_invalid", "The preview is not text. Nothing was written.")
    tokens = shape.get("danger_tokens") if isinstance(shape, dict) else None
    if not tokens:
        raise LedgerProblem("shape_invalid", "A scar needs danger tokens, so nothing was written.")
    with _LOCK:
        view = load()
        if view.status == "unreadable":
            raise LedgerProblem(
                "ledger_unreadable",
                "The ledger file is present but could not be parsed. Leave it in place. Nothing was written.",
            )
        doc = view.doc if view.status == "ok" else _blank()
        for row in doc["scars"]:
            if _same(row, shape):
                return row
        if len(doc["scars"]) >= SCAR_MAX:
            raise LedgerProblem("ledger_full", "The ledger is at its cap. Nothing was written.")
        new_id = max((row["id"] for row in doc["scars"]), default=0) + 1
        row = {
            "arg_keys": list(shape["arg_keys"]),
            "danger_tokens": list(shape["danger_tokens"]),
            "decision": "deny",
            "id": new_id,
            "preview": preview,
            "recorded_at": clock.now_text(),
            "tool": shape["tool"],
        }
        if not _scar_ok(row):
            raise LedgerProblem("shape_invalid", "The shape cannot be stored. Nothing was written.")
        doc["scars"].append(row)
        _write(doc)
        return row


def remove_scar(ident: int) -> tuple[dict, int] | None:
    """Remove one scar by id. Returns the removed row and the count left, or None.

    An absent or unreadable file is not created or replaced.
    """
    with _LOCK:
        view = load()
        if view.status == "unreadable":
            raise LedgerProblem(
                "ledger_unreadable",
                "The ledger file is present but could not be parsed. Leave it in place. Nothing was written.",
            )
        if view.status != "ok":
            return None
        doc = view.doc
        row = next((item for item in doc["scars"] if item["id"] == ident), None)
        if row is None:
            return None
        doc["scars"] = [item for item in doc["scars"] if item["id"] != ident]
        _write(doc)
        return row, len(doc["scars"])
