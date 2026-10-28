"""The only write root is <hermes home>/plugin-data/scar."""

from __future__ import annotations

import os
from pathlib import Path

from .safe_write import WriteRefused, directory_is_real

PLUGIN = "scar"


class StorageError(Exception):
    def __init__(self, error: str):
        self.error_type = "ledger_unreadable"
        self.error = error
        super().__init__(error)


def plugin_root() -> Path:
    try:
        import hermes_constants
    except Exception as exc:
        raise StorageError("Could not import hermes_constants, so nothing was written.") from exc
    getter = getattr(hermes_constants, "get_hermes_home", None)
    if not callable(getter):
        raise StorageError("get_hermes_home is missing, so nothing was written.")
    try:
        home = getter()
    except Exception as exc:
        raise StorageError("get_hermes_home failed, so nothing was written.") from exc
    if isinstance(home, os.PathLike):
        home = os.fspath(home)
    if not isinstance(home, str) or not home.startswith("/") or "\x00" in home:
        raise StorageError("The Hermes home is not an absolute path, so nothing was written.")
    home_path = Path(home)
    # A temp home often sits under a linked ancestor. Follow ancestors so that
    # home can be opened, and still refuse a home path whose own last component
    # is a symlink. plugin-data below that real directory is checked with
    # O_NOFOLLOW, so a linked data directory is not a write target.
    if home_path.is_symlink():
        raise StorageError("The Hermes home is a symlink, so nothing was written.")
    try:
        physical = home_path.resolve()
    except OSError as exc:
        raise StorageError("The Hermes home could not be resolved, so nothing was written.") from exc
    if not physical.is_absolute():
        raise StorageError("The Hermes home is not an absolute path, so nothing was written.")
    root = physical / "plugin-data" / PLUGIN
    try:
        directory_is_real(root)
    except WriteRefused as exc:
        raise StorageError("The plugin data directory is a symlink, so nothing was written.") from exc
    return root
