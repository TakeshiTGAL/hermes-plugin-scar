"""Shared fixtures for the offline tests."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path


def _package():
    name = "scar_plugin"
    if name in sys.modules:
        return sys.modules[name]
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        name,
        root / "__init__.py",
        submodule_search_locations=[str(root)],
    )
    module = importlib.util.module_from_spec(spec)
    module.__package__ = name
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_PKG = _package()
importlib.import_module("scar_plugin.local_host")
clock = sys.modules["scar_plugin.clock"]
gates = sys.modules["scar_plugin.gates"]
hooks = sys.modules["scar_plugin.hooks"]
ledger = sys.modules["scar_plugin.ledger"]
local_host = sys.modules["scar_plugin.local_host"]
redact = sys.modules["scar_plugin.redact"]
schemas = sys.modules["scar_plugin.schemas"]
shape = sys.modules["scar_plugin.shape"]
tools = sys.modules["scar_plugin.tools"]
HANDLERS = tools.HANDLERS
ROOT = Path(__file__).resolve().parents[1]


def use_home(monkeypatch, tmp_path: Path) -> Path:
    home = tmp_path / "hh"
    home.mkdir(exist_ok=True)
    monkeypatch.setenv("HERMES_HOME", str(home))
    module = types.ModuleType("hermes_constants")
    module.get_hermes_home = lambda: str(home)
    monkeypatch.setitem(sys.modules, "hermes_constants", module)
    return home


def call(name: str, args: dict) -> tuple[object, dict]:
    directive = hooks.on_pre_tool_call(name, args)
    body = json.loads(HANDLERS[name](args))
    return directive, body


RM = "rm -rf foo-does-not-exist"
