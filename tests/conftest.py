import sys
import types
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    home = tmp_path / "hh"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    module = types.ModuleType("hermes_constants")
    module.get_hermes_home = lambda: str(home)
    monkeypatch.setitem(sys.modules, "hermes_constants", module)
    return home
