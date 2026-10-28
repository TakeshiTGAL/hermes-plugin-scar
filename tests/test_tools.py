"""Read tools do not write. Each failure kind names itself."""

from __future__ import annotations

import json
import sys
import types

from support import HANDLERS, clock, hooks, ledger


def _body(name: str, args: dict | None = None) -> dict:
    return json.loads(HANDLERS[name]({} if args is None else args))


def test_check_reports_a_read_and_a_miss(monkeypatch):
    monkeypatch.setattr(clock, "now_text", lambda: "2026-10-26T08:45:00+09:00")
    hooks.on_post_approval_response(choice="deny", command="rm -rf foo-does-not-exist")
    missed = _body("scar_check", {"tool": "terminal", "arguments": {"command": "ls"}})
    assert missed["ok"] is True
    assert missed["message"] == "The ledger was read and no scar covers this call."
    hit = _body("scar_check", {"tool": "terminal", "arguments": {"command": "rm -fr other"}})
    assert hit["covered"] is True
    assert hit["message"] == "scar #1, Monday 08:45 +09:00, you pressed deny"
    assert "receipt" not in json.dumps(hit["scar"]).split("you pressed deny")[0] or hit["scar"]["receipt"].endswith("deny")


def test_a_read_of_an_empty_ledger_says_it_was_read(isolated_home):
    root = isolated_home / "plugin-data" / "scar"
    root.mkdir(parents=True)
    (root / "ledger.json").write_text(
        '{"scar_ledger_version": 2, "scars": []}\n',
        encoding="utf-8",
    )
    body = _body("scar_list")
    assert body["message"] == "The ledger was read and it holds no scars."


def test_one_scar_is_singular_and_two_are_plural(monkeypatch):
    monkeypatch.setattr(clock, "now_text", lambda: "2026-10-26T08:45:00+09:00")
    hooks.on_post_approval_response(choice="deny", command="rm -rf foo-does-not-exist")
    one = _body("scar_list")
    assert one["message"] == "The ledger was read and it holds 1 scar."
    hooks.on_post_approval_response(choice="deny", command="rm -r other-name")
    two = _body("scar_list")
    assert two["message"] == "The ledger was read and it holds 2 scars."


def test_bad_argument_rejects_a_caller_clock_and_a_missing_field():
    extra = _body(
        "scar_check",
        {"tool": "terminal", "arguments": {"command": "ls"}, "recorded_at": "2020-01-01T00:00:00+00:00"},
    )
    assert extra["ok"] is False
    assert extra["error_type"] == "bad_argument"
    missing = _body("scar_check", {"tool": "terminal"})
    assert missing["error_type"] == "bad_argument"
    assert missing["next_step"]


def test_shape_invalid_for_a_value_that_cannot_be_compared(isolated_home):
    root = isolated_home / "plugin-data" / "scar"
    root.mkdir(parents=True)
    (root / "ledger.json").write_text(
        '{"scar_ledger_version": 2, "scars": []}\n',
        encoding="utf-8",
    )
    body = _body("scar_check", {"tool": "terminal", "arguments": ["not", "an", "object"]})
    assert body["error_type"] == "shape_invalid"
    assert body["next_step"]


def test_ledger_full_stops_at_the_cap():
    for index in range(ledger.SCAR_MAX):
        ledger.add_scar(
            {"tool": f"t{index}", "arg_keys": ["command"], "danger_tokens": ["rm"]},
            "preview",
        )
    try:
        ledger.add_scar(
            {"tool": "overflow", "arg_keys": ["command"], "danger_tokens": ["rm"]},
            "preview",
        )
    except ledger.LedgerProblem as exc:
        assert exc.kind == "ledger_full"
    else:
        raise AssertionError("cap")


def test_internal_is_its_own_kind(monkeypatch):
    def boom():
        raise RuntimeError("boom")

    monkeypatch.setattr("scar_plugin.tools.load", boom)
    body = _body("scar_list")
    assert body["error_type"] == "internal"
    assert body["next_step"]


def test_a_hand_edited_receipt_is_not_trusted(isolated_home):
    root = isolated_home / "plugin-data" / "scar"
    root.mkdir(parents=True)
    path = root / "ledger.json"
    path.write_text(
        json.dumps(
            {
                "scar_ledger_version": 2,
                "scars": [
                    {
                        "id": 1,
                        "decision": "deny",
                        "recorded_at": "2026-10-26T08:45:00+09:00",
                        "tool": "terminal",
                        "arg_keys": ["command"],
                        "danger_tokens": ["force", "recursive", "rm"],
                        "preview": "rm -rf foo-does-not-exist",
                        "receipt": "scar #1, Friday 00:00, you pressed never",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    before = path.read_bytes()
    view = ledger.load()
    assert view.status == "unreadable"
    body = _body("scar_list")
    assert body["error_type"] == "ledger_unreadable"
    assert "never" not in body["error"]
    assert path.read_bytes() == before


def test_a_symlink_ancestor_still_stores_the_ledger(monkeypatch, tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    jump = tmp_path / "jump"
    jump.symlink_to(real, target_is_directory=True)
    home = jump / "profile"
    home.mkdir()
    module = types.ModuleType("hermes_constants")
    module.get_hermes_home = lambda: str(home)
    monkeypatch.setitem(sys.modules, "hermes_constants", module)
    monkeypatch.setattr(clock, "now_text", lambda: "2026-10-26T08:45:00+09:00")
    hooks.on_post_approval_response(choice="deny", command="rm -rf foo-does-not-exist")
    saved = real / "profile" / "plugin-data" / "scar" / "ledger.json"
    assert saved.is_file()
    assert not saved.is_symlink()


def test_a_symlinked_home_is_not_used(monkeypatch, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "home-link"
    link.symlink_to(outside, target_is_directory=True)
    module = types.ModuleType("hermes_constants")
    module.get_hermes_home = lambda: str(link)
    monkeypatch.setitem(sys.modules, "hermes_constants", module)
    hooks.on_post_approval_response(choice="deny", command="rm -rf foo-does-not-exist")
    assert list(outside.rglob("*")) == []


def test_a_symlink_ledger_is_not_replaced(monkeypatch, isolated_home):
    root = isolated_home / "plugin-data" / "scar"
    root.mkdir(parents=True)
    target = isolated_home / "outside.json"
    target.write_text('{"scar_ledger_version": 2, "scars": []}\n', encoding="utf-8")
    path = root / "ledger.json"
    path.symlink_to(target)
    before = target.read_bytes()
    monkeypatch.setattr(clock, "now_text", lambda: "2026-10-26T08:45:00+09:00")
    hooks.on_post_approval_response(choice="deny", command="rm -rf foo-does-not-exist")
    assert target.read_bytes() == before
    assert path.is_symlink()
