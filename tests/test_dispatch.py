"""The public Hermes dispatcher writes a scar on deny and blocks the next shape."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from support import ROOT

_SRC = os.environ.get("HERMES_SRC", "")
_PY = ""
if _SRC:
    candidate = Path(_SRC).resolve().parents[1] / "venv" / Path(_SRC).resolve().name / "bin" / "python"
    if candidate.is_file():
        _PY = str(candidate)


def _env(home: Path, tmp_path: Path) -> dict:
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "HERMES_HOME": str(home),
        "HERMES_INTERACTIVE": "1",
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": "C.UTF-8",
        "TMPDIR": str(tmp_path),
        "PYTHONPATH": _SRC,
        "PYTHONDONTWRITEBYTECODE": "1",
    }


_NEEDS_SRC = pytest.mark.skipif(
    not _SRC or not Path(_SRC).is_dir() or not _PY, reason="HERMES_SRC is not set"
)


@_NEEDS_SRC
def test_public_dispatcher_keeps_a_deny_and_blocks_the_next_shape(tmp_path):
    home = tmp_path / "empty-home"
    home.mkdir()
    dest = tmp_path / "result.json"
    env = _env(home, tmp_path)
    proc = subprocess.run(
        [ _PY, str(ROOT / "tests" / "drive_card.py"), str(home), _SRC, str(ROOT), str(dest)],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert dest.is_file(), proc.stderr[-2000:]
    payload = json.loads(dest.read_text(encoding="utf-8"))
    assert "error" not in payload, payload
    assert payload["approved"] is False
    ledger = json.loads(payload["ledger"])
    assert ledger["scars"][0]["decision"] == "deny"
    assert ledger["scars"][0]["danger_tokens"] == ["force", "recursive", "rm"]
    assert payload["action"] == "block"
    assert payload["message"].startswith("BLOCKED: scar #1,")
    assert "you pressed deny" in payload["message"]
    assert payload["plain_action"] is None
    assert payload["read_action"] is None
    assert "Do not paraphrase this command and do not run it again." in payload["message"]
    assert "rule_key" not in payload["message"]
    assert payload["shell_action"] == "block"
    assert payload["sh_action"] == "block"
    assert payload["env_action"] == "block"
    assert payload["echo_action"] is None
    assert payload["other_action"] == "block"
    assert payload["other_message"] == "BLOCKED: other plugin"
    assert payload["cron_action"] == "block"
    assert "Do not paraphrase this command and do not run it again." in payload["cron_message"]
    assert payload["cron_approved"] is False
    assert payload["cron_scar_count"] == 1

    dest_yolo = tmp_path / "yolo.json"
    yolo_env = dict(env)
    yolo_env["HERMES_YOLO_MODE"] = "1"
    proc_yolo = subprocess.run(
        [_PY, str(ROOT / "tests" / "drive_card.py"), str(home), _SRC, str(ROOT), str(dest_yolo), "yolo"],
        cwd=str(tmp_path),
        env=yolo_env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert dest_yolo.is_file(), proc_yolo.stderr[-2000:]
    yolo = json.loads(dest_yolo.read_text(encoding="utf-8"))
    assert "error" not in yolo, yolo
    assert yolo["approved"] is True
    assert yolo["action"] == "block"
    assert "Do not paraphrase this command and do not run it again." in yolo["message"]
    assert yolo["plain_action"] is None
    assert yolo["scar_count"] == 1


@_NEEDS_SRC
def test_bound_platform_blocks_forget_and_always_does_not_cover_the_next_call(tmp_path):
    home = tmp_path / "empty-home"
    home.mkdir()
    dest = tmp_path / "gateway.json"
    proc = subprocess.run(
        [_PY, str(ROOT / "tests" / "drive_card.py"), str(home), _SRC, str(ROOT), str(dest), "gateway"],
        cwd=str(tmp_path),
        env=_env(home, tmp_path),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert dest.is_file(), proc.stderr[-2000:]
    out = json.loads(dest.read_text(encoding="utf-8"))
    assert "error" not in out, out
    assert out["keys_differ"] is True
    assert out["first"].startswith("scar_forget:")
    assert out["first"] != out["second"]
    assert out["person_asked"] == 1
    assert out["person_message"]
    assert out["scars"] == 1
    for platform in ("webhook", "api_server", "msgraph_webhook"):
        row = out["rows"][platform]
        assert row["env"] == "", platform
        assert row["public"] == platform
        assert row["asked"] == 0, platform
        assert row["scars"] == 1, platform
        assert "was not forgotten" in row["message"], platform
        assert "was not forgotten" in row["handler"], platform
    assert out["yolo_asked"] == 0
    assert "was not forgotten" in out["yolo_message"]
    assert "was not forgotten" in out["yolo_handler"]
    assert out["off_asked"] == 0
    assert "was not forgotten" in out["off_message"]
    assert "was not forgotten" in out["off_handler"]


@_NEEDS_SRC
def test_public_dispatcher_leaves_ordinary_calls_alone_and_forgets_only_on_approval(tmp_path):
    home = tmp_path / "empty-home"
    home.mkdir()
    dest = tmp_path / "ordinary.json"
    proc = subprocess.run(
        [_PY, str(ROOT / "tests" / "drive_card.py"), str(home), _SRC, str(ROOT), str(dest), "ordinary"],
        cwd=str(tmp_path),
        env=_env(home, tmp_path),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert dest.is_file(), proc.stderr[-2000:]
    out = json.loads(dest.read_text(encoding="utf-8"))
    assert "error" not in out, out
    assert out["guard_approved"] is False
    # Before and after a deny, a sentence, nine file names, and other tools run.
    for row in out["before"] + out["after"]:
        assert row["action"] is None, row
    assert out["blocked"]["action"] == "block"
    assert "you pressed deny" in out["blocked"]["message"]
    # Hermes's own masking and the plugin floor keep the fake keys out.
    for fake in (
        "FAKEtestVALUEnotREAL0123456789abcdefWXYZ",
        "hf_FAKEtestVALUEnotREAL0123456789ab",
        "npm_FAKEtestVALUEnotREAL0123456789",
    ):
        assert fake not in out["secret_ledger"]
        assert fake not in out["scar_list"]
    # No head-and-tail mask either: the last four characters of a fake are gone.
    assert "WXYZ" not in out["secret_ledger"]
    assert "6789" not in out["secret_ledger"]
    assert "AWS_SECRET_ACCESS_KEY" in out["secret_ledger"]
    # scar_forget asks on the Hermes card. A deny leaves the scar and the file.
    assert len(out["asked"]) == 2
    assert out["asked"][0]["choice"] == "deny"
    assert "Forget scar #2" in out["asked"][0]["description"]
    assert "no longer stopped" in out["asked"][0]["description"]
    assert out["long_forget"]["action"] == "block"
    assert "does not fit" in out["long_forget"]["message"]
    assert "no longer stopped" not in out["long_forget"]["message"]
    assert out["long_forget"]["unchanged"] is True
    assert out["long_forget"]["scar_count"] == 1
    assert "BLOCKED" in out["forget_denied"]
    assert out["count_after_forget_deny"] == 2
    assert json.loads(out["forget_once"])["status"] == "forgotten"
    assert out["count_after_forget_once"] == 1
    assert out["after_forget"]["action"] is None
    assert out["still_blocked"]["action"] == "block"
    # A broken ledger stops only the rm command, and the file is left in place.
    for row in out["broken"][:-1]:
        assert row["action"] is None, row
    assert out["broken"][-1]["action"] == "block"
    assert "could not be read" in out["broken"][-1]["message"]
    assert out["broken_bytes"] == "{not json"
    held = out["held"]
    assert held["cron_asked"] == 0
    assert held["identity_asked"] == 0
    assert "was not forgotten" in held["cron_result"]
    assert "was not forgotten" in held["identity_result"]
    assert held["scar_count"] == 1
    surface = out["skill_surface"]
    assert surface["with_skills"] is True
    assert surface["scar_tools_off"] is True
    assert surface["wide"] is True
    assert surface["narrow"] is False
    assert surface["startup"] is False
    assert surface["skills_list"] is True
