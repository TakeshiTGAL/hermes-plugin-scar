"""A deny writes a scar. The next same shape stops. Ordinary calls do not."""

import json
import sys
import types
from pathlib import Path

from support import HANDLERS, RM, clock, hooks, ledger, shape

WHEN = "2026-10-26T08:45:00+09:00"
SECRET_KEY = "sk-testscarpluginvalue"
SECRET_GH = "ghp_scarpluginfakevalue"
SECRET_PAT = "github_pat_scarpluginfakevalue"
SECRET_BOT = "xoxb-1234567890-abcdef"
SECRET_USER = "xoxp-1234567890-abcdef"
SECRET_AKIA = "AKIAIOSFODNN7EXAMPLE"
SECRET_PW = "hunter2xyz"
SECRET_URL = "pa55word"
SECRET_AWS = "FAKEtestVALUEnotREAL0123456789abcdefWXYZ"
SECRET_HF = "hf_FAKEtestVALUEnotREAL0123456789ab"
SECRET_GL = "glpat-FAKEtestVALUEnotREAL01"
SECRET_GOOGLE = "AIzaFAKEtestVALUEnotREAL0123456789abcdef"
SECRET_SSH = "FAKEsshpassVALUE"
SECRET_MYSQL = "FAKEmysqlVALUE"
SENTENCE = "The build finished and all the tests passed on the main branch today."
NINE = "touch a.txt b.txt c.txt d.txt e.txt f.txt g.txt h.txt i.txt"


def _deny(monkeypatch, command: str, choice: str = "deny", **extra):
    monkeypatch.setattr(clock, "now_text", lambda: WHEN)
    hooks.on_post_approval_response(choice=choice, command=command, **extra)


def _ledger(home: Path) -> dict:
    return json.loads((home / "plugin-data" / "scar" / "ledger.json").read_text(encoding="utf-8"))


def test_deny_writes_a_scar_and_the_same_shape_blocks(monkeypatch, isolated_home):
    _deny(monkeypatch, RM, recorded_at="1999-01-01T00:00:00+00:00")
    doc = _ledger(isolated_home)
    row = doc["scars"][0]
    assert row["decision"] == "deny"
    assert row["recorded_at"] == WHEN
    assert row["danger_tokens"] == ["force", "recursive", "rm"]
    assert "1999" not in json.dumps(doc)
    blocked = hooks.on_pre_tool_call(
        "terminal",
        {"command": "rm -fr foo-does-not-exist", "timeout": 9, "background": True},
    )
    assert blocked["action"] == "block"
    assert blocked["message"] == (
        "BLOCKED: scar #1, Monday 08:45 +09:00, you pressed deny. "
        "Do not paraphrase this command and do not run it again."
    )
    for command in (
        "bash -c 'rm -rf foo-does-not-exist'",
        "sh -c 'rm -rf foo-does-not-exist'",
        "env -u PATH rm -rf foo-does-not-exist",
    ):
        again = hooks.on_pre_tool_call("terminal", {"command": command})
        assert again["action"] == "block", command
    assert "rule_key" not in blocked


def test_other_choices_and_plain_commands_do_not_write(monkeypatch, isolated_home):
    for choice in ("once", "session", "always", "timeout", "cancelled", "smart_approve", "smart_deny", "unlisted", "never"):
        _deny(monkeypatch, RM, choice=choice)
    _deny(monkeypatch, "ls")
    _deny(monkeypatch, "echo rm -rf is dangerous")
    assert not (isolated_home / "plugin-data").exists()
    assert hooks.on_pre_tool_call("terminal", {"command": "ls"}) is None
    assert hooks.on_pre_tool_call("terminal", {"command": "git status"}) is None
    assert hooks.on_pre_tool_call("read_file", {"path": "notes.txt"}) is None


def test_unattended_and_isolation_do_not_write(monkeypatch, isolated_home):
    monkeypatch.setenv("HERMES_CRON_SESSION", "1")
    _deny(monkeypatch, RM)
    monkeypatch.delenv("HERMES_CRON_SESSION")
    monkeypatch.setenv("HERMES_SINGLE_QUERY_SESSION", "1")
    _deny(monkeypatch, RM)
    monkeypatch.delenv("HERMES_SINGLE_QUERY_SESSION")
    monkeypatch.setenv("HERMES_SESSION_PLATFORM", "webhook")
    _deny(monkeypatch, RM)
    monkeypatch.delenv("HERMES_SESSION_PLATFORM")
    monkeypatch.setenv("HERMES_SESSION_PLATFORM", "api_server")
    _deny(monkeypatch, RM)
    monkeypatch.delenv("HERMES_SESSION_PLATFORM")
    monkeypatch.setenv("HERMES_PLUGIN_HOST_PROCESS", "1")
    _deny(monkeypatch, RM)
    assert not (isolated_home / "plugin-data").exists()


def test_an_existing_scar_still_blocks_when_unattended(monkeypatch, isolated_home):
    _deny(monkeypatch, RM)
    monkeypatch.setenv("HERMES_CRON_SESSION", "1")
    blocked = hooks.on_pre_tool_call("terminal", {"command": "rm --recursive --force foo-does-not-exist"})
    assert blocked["action"] == "block"


def test_rm_without_force_does_not_match_an_rf_scar(monkeypatch):
    _deny(monkeypatch, RM)
    assert hooks.on_pre_tool_call("terminal", {"command": "rm -r foo-does-not-exist"}) is None


def test_a_weaker_scar_blocks_a_stronger_call(monkeypatch):
    _deny(monkeypatch, "rm -r foo-does-not-exist")
    blocked = hooks.on_pre_tool_call("terminal", {"command": "rm -rf other-name"})
    assert blocked["action"] == "block"


def test_secrets_are_gone_and_the_rm_tokens_remain(monkeypatch, isolated_home):
    command = (
        "rm -rf ./build --password "
        + SECRET_PW
        + " GITHUB_TOKEN="
        + SECRET_GH
        + ' {"api_key": "'
        + SECRET_KEY
        + '"} {"token": "'
        + SECRET_GH
        + '"} Authorization: Bearer '
        + SECRET_GH
        + " postgres://user:"
        + SECRET_URL
        + "@db.example/app "
        + SECRET_PAT
        + " "
        + SECRET_BOT
        + " "
        + SECRET_USER
        + " "
        + SECRET_AKIA
    )
    _deny(monkeypatch, command)
    raw = (isolated_home / "plugin-data" / "scar" / "ledger.json").read_text(encoding="utf-8")
    for secret in (SECRET_KEY, SECRET_GH, SECRET_PAT, SECRET_BOT, SECRET_USER, SECRET_AKIA, SECRET_PW, SECRET_URL):
        assert secret not in raw
    for prefix in ("xoxb-", "xoxp-", "ghp_", "github_pat_", "sk-", "AKIA"):
        assert prefix not in raw
    assert _ledger(isolated_home)["scars"][0]["danger_tokens"] == ["force", "recursive", "rm"]
    listed = json.loads(HANDLERS["scar_list"]({}))
    assert SECRET_GH not in json.dumps(listed)


def test_a_second_deny_keeps_the_first_receipt(monkeypatch, isolated_home):
    _deny(monkeypatch, RM)
    monkeypatch.setattr(clock, "now_text", lambda: "2026-11-02T01:02:00+09:00")
    hooks.on_post_approval_response(choice="deny", command="rm -fr foo-does-not-exist")
    doc = _ledger(isolated_home)
    assert len(doc["scars"]) == 1
    assert doc["scars"][0]["recorded_at"] == WHEN


def test_absent_ledger_does_not_block_and_does_not_create_a_file(isolated_home):
    assert hooks.on_pre_tool_call("terminal", {"command": RM}) is None
    assert hooks.on_pre_tool_call("read_file", {"path": "notes.txt"}) is None
    body = json.loads(HANDLERS["scar_list"]({}))
    assert body["message"] == "The ledger file is absent."
    assert "zero" not in body["message"]
    assert not (isolated_home / "plugin-data").exists()


def test_an_unreadable_ledger_stops_only_rm_and_is_not_replaced(monkeypatch, isolated_home):
    root = isolated_home / "plugin-data" / "scar"
    root.mkdir(parents=True)
    path = root / "ledger.json"
    path.write_text('{"scar_ledger_version": 1, "scars": [], "pairs": []}', encoding="utf-8")
    before = path.read_bytes()
    _deny(monkeypatch, RM)
    assert path.read_bytes() == before
    assert hooks.on_pre_tool_call("terminal", {"command": "ls"}) is None
    assert hooks.on_pre_tool_call("terminal", {"command": NINE}) is None
    assert hooks.on_pre_tool_call("write_file", {"path": "n.txt", "content": SENTENCE}) is None
    assert hooks.on_pre_tool_call("read_file", {"path": "notes.txt"}) is None
    blocked = hooks.on_pre_tool_call("terminal", {"command": "rm -rf other"})
    assert blocked["message"] == hooks.UNREADABLE
    long_ls = "ls " + ("a" * shape.MAX_TEXT)
    nine_nice = ("nice " * (shape.MAX_WRAP + 1)) + "ls"
    assert hooks.on_pre_tool_call("terminal", {"command": long_ls}) is None
    assert hooks.on_pre_tool_call("terminal", {"command": nine_nice}) is None
    assert path.read_bytes() == before
    assert hooks.on_pre_tool_call("scar_list", {}) is None
    body = json.loads(HANDLERS["scar_list"]({}))
    assert body["ok"] is False
    assert body["error_type"] == "ledger_unreadable"
    assert path.read_bytes() == before


def test_a_huge_call_is_blocked_only_on_a_scarred_tool(monkeypatch):
    huge = {"command": "y" * (ledger.FILE_MAX + 1)}
    assert hooks.on_pre_tool_call("terminal", huge) is None
    _deny(monkeypatch, RM)
    blocked = hooks.on_pre_tool_call("terminal", huge)
    assert blocked["message"] == hooks.UNCOMPARED
    big = {"path": "big.txt", "content": "y" * (ledger.FILE_MAX + 1)}
    assert hooks.on_pre_tool_call("write_file", big) is None
    # A scar kept the command key only, so another key of the same tool is not read.
    assert hooks.on_pre_tool_call("terminal", {"command": "ls", "stdin": "y" * (ledger.FILE_MAX + 1)}) is None


def test_reads_do_not_change_the_file(monkeypatch, isolated_home):
    _deny(monkeypatch, RM)
    path = isolated_home / "plugin-data" / "scar" / "ledger.json"
    before = path.read_bytes()
    HANDLERS["scar_list"]({})
    HANDLERS["scar_check"]({"tool": "terminal", "arguments": {"command": "ls"}})
    assert path.read_bytes() == before


def test_ordinary_calls_after_a_scar_are_not_stopped(monkeypatch):
    _deny(monkeypatch, RM)
    calls = [
        ("terminal", {"command": NINE}),
        ("terminal", {"command": "git add a.py b.py c.py d.py e.py f.py g.py h.py"}),
        ("terminal", {"command": "echo " + SENTENCE}),
        ("terminal", {"command": " ".join(["word"] * 100)}),
        ("terminal", {"command": "ls", "workdir": "/tmp/build", "timeout": 9}),
        ("write_file", {"path": "notes.txt", "content": SENTENCE}),
        ("write_file", {"path": "long.txt", "content": " ".join([SENTENCE] * 3000)}),
        ("web_search", {"query": "how to configure nginx reverse proxy with ssl on ubuntu"}),
        ("send_message", {"target": "telegram", "message": SENTENCE}),
        ("patch", {"nested": {"deep": {"deeper": {"a": {"b": {"c": {"d": {"e": {"f": "x"}}}}}}}}}),
        ("read_file", {"path": "README.md"}),
    ]
    for tool, args in calls:
        assert hooks.on_pre_tool_call(tool, args) is None, (tool, args)
    assert hooks.on_pre_tool_call("terminal", {"command": "sudo -u root rm -rf x"})["action"] == "block"
    assert hooks.on_pre_tool_call("terminal", {"command": "timeout 5 xargs -n 1 rm -rf"})["action"] == "block"


def test_floor_secrets_are_gone_from_the_ledger_and_the_list(monkeypatch, isolated_home):
    command = (
        "AWS_SECRET_ACCESS_KEY=" + SECRET_AWS
        + " HF_TOKEN=x " + SECRET_HF
        + " " + SECRET_GL
        + " " + SECRET_GOOGLE
        + " sshpass -p " + SECRET_SSH + " ssh host"
        + "; mysql -uroot -p" + SECRET_MYSQL + " db"
        + "; rm -rf build"
    )
    _deny(monkeypatch, command)
    raw = (isolated_home / "plugin-data" / "scar" / "ledger.json").read_text(encoding="utf-8")
    listed = HANDLERS["scar_list"]({})
    for secret in (SECRET_AWS, SECRET_HF, SECRET_GL, SECRET_GOOGLE, SECRET_SSH, SECRET_MYSQL):
        assert secret not in raw, secret
        assert secret not in listed, secret
    assert _ledger(isolated_home)["scars"][0]["danger_tokens"] == ["force", "recursive", "rm"]


def test_an_old_ledger_preview_is_masked_again_when_listed(monkeypatch, isolated_home):
    _deny(monkeypatch, RM)
    path = isolated_home / "plugin-data" / "scar" / "ledger.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["scars"][0]["preview"] = "AWS_SECRET_ACCESS_KEY=" + SECRET_AWS + " rm -rf build"
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert SECRET_AWS not in HANDLERS["scar_list"]({})


def test_a_deny_on_a_plugin_card_is_not_a_scar(monkeypatch, isolated_home):
    _deny(monkeypatch, "<scar_forget> (plugin approval rule) rm -rf x", pattern_key="plugin_rule:scar_forget:abc")
    _deny(monkeypatch, "computer_use: type rm -rf x", pattern_key="cua:type:background")
    assert not (isolated_home / "plugin-data").exists()


def test_a_forget_question_that_does_not_fit_is_not_sent(monkeypatch, isolated_home):
    _deny(monkeypatch, RM)
    path = isolated_home / "plugin-data" / "scar" / "ledger.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["scars"][0]["preview"] = "x" * 500
    path.write_text(json.dumps(doc), encoding="utf-8")
    before = path.read_bytes()
    directive = hooks.on_pre_tool_call("scar_forget", {"id": 1})
    assert directive["action"] == "block"
    assert directive["message"] == hooks.FORGET_CUT
    assert "no longer stopped" not in directive["message"]
    assert "rule_key" not in directive
    assert path.read_bytes() == before
    doc["scars"][0]["preview"] = "rm -rf foo-does-not-exist"
    path.write_text(json.dumps(doc), encoding="utf-8")
    short = hooks.on_pre_tool_call("scar_forget", {"id": 1})
    assert short["action"] == "approve"
    assert short["message"].endswith("After this, that shape is no longer stopped.")
    assert "foo-does-not-exist" in short["message"]
    assert hooks._card_line_count(short["message"]) <= hooks._CARD_LINES
    monkeypatch.setenv("HERMES_YOLO_MODE", "1")
    doc["scars"][0]["preview"] = "x" * 500
    path.write_text(json.dumps(doc), encoding="utf-8")
    yolo = hooks.on_pre_tool_call("scar_forget", {"id": 1})
    assert yolo["action"] == "block"
    assert yolo["message"] == hooks.FORGET_CUT
    assert path.read_text(encoding="utf-8").count('"id": 1') == 1


def test_forget_asks_with_a_key_for_that_one_scar(monkeypatch, isolated_home):
    _deny(monkeypatch, RM)
    directive = hooks.on_pre_tool_call("scar_forget", {"id": 1})
    assert directive["action"] == "approve"
    assert directive["message"].startswith("Forget scar #1, Monday 08:45 +09:00, you pressed deny")
    assert directive["rule_key"].startswith("scar_forget:")
    assert len(directive["rule_key"]) == len("scar_forget:") + 16
    same = hooks.on_pre_tool_call("scar_forget", {"id": 1})
    assert same["action"] == "approve"
    assert same["rule_key"] != directive["rule_key"]
    assert hooks.on_pre_tool_call("scar_forget", {"id": 9}) is None
    assert hooks.on_pre_tool_call("scar_forget", {"id": True}) is None
    body = json.loads(HANDLERS["scar_forget"]({"id": 1}))
    assert body["status"] == "forgotten"
    assert body["message"].endswith("it holds 0 scars.")
    assert hooks.on_pre_tool_call("terminal", {"command": RM}) is None
    # The same id later names a different scar, so an always choice does not carry over.
    monkeypatch.setattr(clock, "now_text", lambda: "2026-11-02T01:02:00+09:00")
    hooks.on_post_approval_response(choice="deny", command=RM)
    again = hooks.on_pre_tool_call("scar_forget", {"id": 1})
    assert again["rule_key"] != directive["rule_key"]


def test_a_bound_platform_blocks_forget_when_the_process_env_is_empty(monkeypatch, isolated_home):
    _deny(monkeypatch, RM)
    path = isolated_home / "plugin-data" / "scar" / "ledger.json"
    before = path.read_bytes()
    module = types.ModuleType("gateway.session_context")
    bound = {"platform": "webhook"}

    def reader(name, default=""):
        if name == "HERMES_SESSION_PLATFORM":
            return bound["platform"]
        return default

    module.get_session_env = reader
    monkeypatch.setitem(sys.modules, "gateway.session_context", module)
    monkeypatch.delenv("HERMES_SESSION_PLATFORM", raising=False)
    for platform in ("webhook", "api_server", "msgraph_webhook"):
        bound["platform"] = platform
        directive = hooks.on_pre_tool_call("scar_forget", {"id": 1})
        assert directive["action"] == "block", platform
        assert "was not forgotten" in directive["message"]
        body = json.loads(HANDLERS["scar_forget"]({"id": 1}))
        assert body["error_type"] == "unattended", platform
        assert path.read_bytes() == before
    bound["platform"] = "telegram"
    asked = hooks.on_pre_tool_call("scar_forget", {"id": 1})
    assert asked["action"] == "approve"
    assert path.read_bytes() == before


def test_forget_is_refused_when_nobody_can_answer(monkeypatch, isolated_home):
    _deny(monkeypatch, RM)
    path = isolated_home / "plugin-data" / "scar" / "ledger.json"
    before = path.read_bytes()
    lanes = (
        {"HERMES_CRON_SESSION": "1"},
        {"HERMES_SINGLE_QUERY_SESSION": "1"},
        {"HERMES_SESSION_PLATFORM": "webhook"},
        {"HERMES_SESSION_PLATFORM": "msgraph_webhook"},
        {"HERMES_SESSION_PLATFORM": "api_server"},
        {"HERMES_PLUGIN_HOST_PROCESS": "1"},
        {"HERMES_CRON_SESSION": "1", "HERMES_YOLO_MODE": "1"},
    )
    for lane in lanes:
        for name in (
            "HERMES_CRON_SESSION",
            "HERMES_SINGLE_QUERY_SESSION",
            "HERMES_SESSION_PLATFORM",
            "HERMES_PLUGIN_HOST_PROCESS",
            "HERMES_YOLO_MODE",
        ):
            monkeypatch.delenv(name, raising=False)
        for name, value in lane.items():
            monkeypatch.setenv(name, value)
        directive = hooks.on_pre_tool_call("scar_forget", {"id": 1})
        assert directive["action"] == "block", lane
        assert "was not forgotten" in directive["message"]
        body = json.loads(HANDLERS["scar_forget"]({"id": 1}))
        assert body["error_type"] == "unattended", lane
        assert path.read_bytes() == before
    for name in (
        "HERMES_CRON_SESSION",
        "HERMES_SINGLE_QUERY_SESSION",
        "HERMES_SESSION_PLATFORM",
        "HERMES_PLUGIN_HOST_PROCESS",
        "HERMES_YOLO_MODE",
    ):
        monkeypatch.delenv(name, raising=False)
    again = hooks.on_pre_tool_call("scar_forget", {"id": 1})
    assert again["action"] == "approve"
    assert hooks.on_pre_tool_call("terminal", {"command": "ls"}) is None


def test_forget_reports_a_missing_scar_and_writes_nothing(isolated_home):
    body = json.loads(HANDLERS["scar_forget"]({"id": 1}))
    assert body["error_type"] == "not_found"
    assert not (isolated_home / "plugin-data").exists()
    bad = json.loads(HANDLERS["scar_forget"]({"id": "1"}))
    assert bad["error_type"] == "bad_argument"


def test_forget_leaves_a_broken_ledger_in_place(isolated_home):
    root = isolated_home / "plugin-data" / "scar"
    root.mkdir(parents=True)
    path = root / "ledger.json"
    path.write_text("{not json", encoding="utf-8")
    body = json.loads(HANDLERS["scar_forget"]({"id": 1}))
    assert body["error_type"] == "ledger_unreadable"
    assert path.read_text(encoding="utf-8") == "{not json"
