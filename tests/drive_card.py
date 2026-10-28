"""Drive the public Hermes approval gate. Invoked as a subprocess."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _other_plugin(home: Path) -> None:
    root = home / "plugins" / "other-block"
    root.mkdir(parents=True, exist_ok=True)
    (root / "plugin.yaml").write_text(
        "name: other-block\n"
        "version: 0.0.1\n"
        "manifest_version: 2\n"
        "description: Block one marker tool in the dispatcher test.\n"
        "author: TakeshiTGAL\n"
        "license: MIT\n"
        "provides_hooks:\n"
        "  - pre_tool_call\n",
        encoding="utf-8",
    )
    (root / "__init__.py").write_text(
        "def register(ctx):\n"
        "    def on_pre_tool_call(tool_name='', args=None, **kwargs):\n"
        "        if tool_name == 'marker_tool':\n"
        "            return {'action': 'block', 'message': 'BLOCKED: other plugin'}\n"
        "        return None\n"
        "    ctx.register_hook('pre_tool_call', on_pre_tool_call)\n",
        encoding="utf-8",
    )


def _scar_count(path: Path) -> int:
    if not path.is_file():
        return 0
    return len(json.loads(path.read_text(encoding="utf-8"))["scars"])


SENTENCE = "The build finished and all the tests passed on the main branch today."
ORDINARY = [
    ("terminal", {"command": "touch a.txt b.txt c.txt d.txt e.txt f.txt g.txt h.txt i.txt"}),
    ("terminal", {"command": "git add a.py b.py c.py d.py e.py f.py g.py h.py"}),
    ("terminal", {"command": "echo " + SENTENCE}),
    ("terminal", {"command": "ls"}),
    ("web_search", {"query": "how to configure nginx reverse proxy with ssl on ubuntu"}),
    ("write_file", {"path": "notes.txt", "content": SENTENCE}),
    ("write_file", {"path": "long.txt", "content": " ".join([SENTENCE] * 2000)}),
    ("send_message", {"target": "telegram", "message": SENTENCE}),
    ("read_file", {"path": "README.md"}),
]
FAKE_AWS = "FAKEtestVALUEnotREAL0123456789abcdefWXYZ"
FAKE_HF = "hf_FAKEtestVALUEnotREAL0123456789ab"
# The plugin floor has no npm pattern. Only Hermes's public redactor knows it.
FAKE_NPM = "npm_FAKEtestVALUEnotREAL0123456789"


def _directives(calls):
    from hermes_cli.plugins import get_pre_tool_call_directive

    out = []
    for tool, args in calls:
        action, message = get_pre_tool_call_directive(tool, args)
        out.append({"tool": tool, "action": action, "message": message})
    return out


def _ordinary(home: Path, ledger_path: Path, deny) -> dict:
    """After one deny, ordinary calls are not read. Secrets do not reach the ledger.

    scar_forget goes through Hermes's own approval card. A broken ledger stops
    only an rm command.
    """
    from model_tools import handle_function_call
    from tools.approval import check_all_command_guards
    from tools.terminal_tool import set_approval_callback

    before = _directives(ORDINARY)
    guard = check_all_command_guards("rm -rf foo-does-not-exist", "local", approval_callback=deny)
    after = _directives(ORDINARY)
    blocked = _directives([("terminal", {"command": "rm -fr foo-does-not-exist"})])[0]
    check_all_command_guards(
        "AWS_SECRET_ACCESS_KEY=" + FAKE_AWS + " HF=" + FAKE_HF + " NPMRC=" + FAKE_NPM + " rm -r -v build",
        "local",
        approval_callback=deny,
    )
    secret_ledger = ledger_path.read_text(encoding="utf-8")
    listed = handle_function_call("scar_list", {})

    asked = []

    def answer(choice):
        def cb(command, description, **kwargs):
            asked.append({"command": command, "description": description, "choice": choice})
            return choice
        return cb

    set_approval_callback(answer("deny"))
    forget_denied = handle_function_call("scar_forget", {"id": 2})
    count_after_forget_deny = _scar_count(ledger_path)
    set_approval_callback(answer("once"))
    forget_once = handle_function_call("scar_forget", {"id": 2})
    count_after_forget_once = _scar_count(ledger_path)
    after_forget = _directives([("terminal", {"command": "rm -r -v build"})])[0]
    still_blocked = _directives([("terminal", {"command": "rm -rf -v build"})])[0]
    set_approval_callback(None)
    held = _forget_held_by_allowlist(ledger_path)
    long_forget = _forget_question_that_does_not_fit(ledger_path)

    ledger_path.write_text("{not json", encoding="utf-8")
    long_ls = "ls " + ("a" * 200_000)
    nine_nice = ("nice " * 9) + "ls"
    broken = _directives(
        ORDINARY
        + [
            ("terminal", {"command": long_ls}),
            ("terminal", {"command": nine_nice}),
            ("terminal", {"command": "rm -rf foo-does-not-exist"}),
        ]
    )
    broken_bytes = ledger_path.read_text(encoding="utf-8")
    return {
        "guard_approved": bool(guard.get("approved")) if isinstance(guard, dict) else True,
        "before": before,
        "after": after,
        "blocked": blocked,
        "secret_ledger": secret_ledger,
        "scar_list": listed,
        "asked": asked,
        "forget_denied": forget_denied,
        "count_after_forget_deny": count_after_forget_deny,
        "forget_once": forget_once,
        "count_after_forget_once": count_after_forget_once,
        "after_forget": after_forget,
        "still_blocked": still_blocked,
        "broken": broken,
        "broken_bytes": broken_bytes,
        "held": held,
        "long_forget": long_forget,
        "skill_surface": _skill_surface(),
    }


def _skill_surface() -> dict:
    """The public skills prompt, the startup catalog, and skills_list."""
    from agent.prompt_builder import build_skills_system_prompt
    from agent.system_prompt import _skills_prompt
    from tools.skills_tool import _find_all_skills, skills_list

    skills_tools = {"skills_list", "skill_view", "skill_manage", "terminal"}
    with_skills = build_skills_system_prompt(
        available_tools=skills_tools,
        available_toolsets={"skills", "terminal"},
    )
    scar_off = build_skills_system_prompt(
        available_tools={"skills_list", "skill_view", "skill_manage", "terminal", "read_file"},
        available_toolsets={"skills", "terminal", "file"},
    )

    class _Narrow:
        valid_tool_names = {"terminal", "scar_check", "scar_list", "scar_forget"}
        platform = "cli"

    class _Wide:
        valid_tool_names = skills_tools
        platform = "cli"

    startup = [row.get("name") for row in _find_all_skills()]
    return {
        "with_skills": "scar:keep-a-scar" in with_skills,
        "scar_tools_off": "scar:keep-a-scar" in scar_off,
        "narrow": "scar:keep-a-scar" in _skills_prompt(_Narrow()),
        "wide": "scar:keep-a-scar" in _skills_prompt(_Wide()),
        "startup": any(name == "scar:keep-a-scar" for name in startup),
        "skills_list": "scar:keep-a-scar" in skills_list(),
    }


def _forget_question_that_does_not_fit(ledger_path: Path) -> dict:
    """A 500-character preview makes a question the card would cut. It is not sent."""
    from hermes_cli.plugins import get_pre_tool_call_directive

    doc = json.loads(ledger_path.read_text(encoding="utf-8"))
    doc["scars"][0]["preview"] = "x" * 500
    body = json.dumps(doc)
    ledger_path.write_text(body, encoding="utf-8")
    action, message = get_pre_tool_call_directive("scar_forget", {"id": doc["scars"][0]["id"]})
    return {
        "action": action,
        "message": message,
        "unchanged": ledger_path.read_text(encoding="utf-8") == body,
        "scar_count": _scar_count(ledger_path),
    }


def _forget_held_by_allowlist(ledger_path: Path) -> dict:
    """A permanent allowlist entry is approved before cron deny. The hook blocks first."""
    from cron.execution_identity import enter_cron_execution, exit_cron_execution
    from hermes_cli.plugins import invoke_hook
    from model_tools import handle_function_call
    from tools.approval import approve_permanent
    from tools.terminal_tool import set_approval_callback

    def _rule() -> str:
        results = invoke_hook(
            "pre_tool_call", tool_name="scar_forget", args={"id": 1}, session_id="held", task_id="held",
        )
        approve = next(item for item in results if isinstance(item, dict) and item.get("action") == "approve")
        return approve["rule_key"]

    # Taken while a person is present, then the scar is left in place on purpose.
    os.environ.pop("HERMES_CRON_SESSION", None)
    rule_key = _rule()
    approve_permanent("plugin_rule:" + rule_key)
    asked = {"n": 0}

    def cb(*_args, **_kwargs):
        asked["n"] += 1
        return "deny"

    set_approval_callback(cb)
    os.environ["HERMES_CRON_SESSION"] = "1"
    try:
        cron_result = handle_function_call(
            "scar_forget", {"id": 1}, task_id="cron", session_id="cron", tool_call_id="cron", turn_id="cron",
        )
    finally:
        os.environ.pop("HERMES_CRON_SESSION", None)
    cron_asked = asked["n"]
    os.environ.pop("HERMES_CRON_SESSION", None)
    token = enter_cron_execution(
        {"id": "held-job", "name": "held"},
        "held-exec",
        {"source": "builtin", "started_at": "2026-10-28T08:00:00Z"},
    )
    try:
        identity_result = handle_function_call(
            "scar_forget", {"id": 1}, task_id="ident", session_id="ident",
            tool_call_id="ident", turn_id="ident",
        )
    finally:
        exit_cron_execution(token)
        set_approval_callback(None)
    return {
        "cron_result": cron_result,
        "cron_asked": cron_asked,
        "identity_result": identity_result,
        "identity_asked": asked["n"],
        "scar_count": _scar_count(ledger_path),
    }


def _gateway_forget(home: Path) -> dict:
    """Bound platform with an empty process env, and a new rule key on every forget."""
    from gateway.session_context import get_session_env, reset_session_vars, set_session_vars
    from hermes_cli.plugins import invoke_hook, resolve_pre_tool_block
    from model_tools import handle_function_call
    from tools.approval import approve_permanent, check_all_command_guards
    from tools.terminal_tool import set_approval_callback

    ledger_path = home / "plugin-data" / "scar" / "ledger.json"
    reset_session_vars()

    def deny(command, description, **kwargs):
        return "deny"

    check_all_command_guards(
        "rm -rf foo-does-not-exist",
        "local",
        approval_callback=deny,
    )

    def rule() -> str:
        results = invoke_hook(
            "pre_tool_call",
            tool_name="scar_forget",
            args={"id": 1},
            session_id="person",
            task_id="person",
        )
        approve = next(item for item in results if isinstance(item, dict) and item.get("action") == "approve")
        return approve["rule_key"]

    first = rule()
    second = rule()
    approve_permanent("plugin_rule:" + first)
    asked = {"n": 0}

    def cb(*_args, **_kwargs):
        asked["n"] += 1
        return "deny"

    def _text(body: object) -> str:
        return body if isinstance(body, str) else json.dumps(body)

    set_approval_callback(cb)
    try:
        person_message = resolve_pre_tool_block(
            "scar_forget", {"id": 1}, session_id="person", task_id="person",
        )
        person_asked = asked["n"]
        rows = {}
        for platform in ("webhook", "api_server", "msgraph_webhook"):
            asked["n"] = 0
            os.environ.pop("HERMES_SESSION_PLATFORM", None)
            os.environ.pop("HERMES_YOLO_MODE", None)
            set_session_vars(platform=platform, cron_session="")
            try:
                message = resolve_pre_tool_block(
                    "scar_forget", {"id": 1}, session_id="wh", task_id="wh",
                )
                body = handle_function_call(
                    "scar_forget",
                    {"id": 1},
                    task_id="wh",
                    session_id="wh",
                    tool_call_id="wh",
                    turn_id="wh",
                )
                rows[platform] = {
                    "env": os.environ.get("HERMES_SESSION_PLATFORM", ""),
                    "public": get_session_env("HERMES_SESSION_PLATFORM", ""),
                    "message": message,
                    "handler": _text(body),
                    "asked": asked["n"],
                    "scars": _scar_count(ledger_path),
                }
            finally:
                reset_session_vars()
        asked["n"] = 0
        os.environ["HERMES_YOLO_MODE"] = "1"
        set_session_vars(platform="webhook", cron_session="")
        try:
            yolo_message = resolve_pre_tool_block(
                "scar_forget", {"id": 1}, session_id="wh", task_id="wh",
            )
            yolo_body = handle_function_call(
                "scar_forget",
                {"id": 1},
                task_id="wh",
                session_id="wh",
                tool_call_id="wh",
                turn_id="wh",
            )
            yolo_asked = asked["n"]
        finally:
            reset_session_vars()
            os.environ.pop("HERMES_YOLO_MODE", None)
        (home / "config.yaml").write_text(
            "plugins:\n  enabled:\n    - scar\napprovals:\n  mode: off\n",
            encoding="utf-8",
        )
        asked["n"] = 0
        set_session_vars(platform="webhook", cron_session="")
        try:
            off_message = resolve_pre_tool_block(
                "scar_forget", {"id": 1}, session_id="wh", task_id="wh",
            )
            off_body = handle_function_call(
                "scar_forget",
                {"id": 1},
                task_id="off",
                session_id="off",
                tool_call_id="off",
                turn_id="off",
            )
            off_asked = asked["n"]
        finally:
            reset_session_vars()
    finally:
        set_approval_callback(None)
        reset_session_vars()
    return {
        "first": first,
        "second": second,
        "keys_differ": first != second,
        "person_asked": person_asked,
        "person_message": person_message,
        "rows": rows,
        "yolo_message": yolo_message,
        "yolo_handler": _text(yolo_body),
        "yolo_asked": yolo_asked,
        "off_message": off_message,
        "off_handler": _text(off_body),
        "off_asked": off_asked,
        "scars": _scar_count(ledger_path),
    }


def main() -> int:
    home, src, plugin, dest = sys.argv[1:5]
    mode = sys.argv[5] if len(sys.argv) > 5 else "deny"
    os.environ["HERMES_HOME"] = home
    os.environ["HOME"] = home
    os.environ["HERMES_INTERACTIVE"] = "1"
    for name in (
        "HERMES_CRON_SESSION",
        "HERMES_SINGLE_QUERY_SESSION",
        "HERMES_SESSION_PLATFORM",
        "HERMES_PLUGIN_HOST_PROCESS",
    ):
        os.environ.pop(name, None)
    if mode != "yolo":
        os.environ.pop("HERMES_YOLO_MODE", None)
    sys.path.insert(0, src)
    config = Path(home) / "config.yaml"
    config.write_text(
        "plugins:\n  enabled:\n    - scar\n    - other-block\napprovals:\n  mode: manual\n",
        encoding="utf-8",
    )
    link = Path(home) / "plugins" / "scar"
    link.parent.mkdir(parents=True, exist_ok=True)
    if not link.exists():
        link.symlink_to(plugin, target_is_directory=True)
    _other_plugin(Path(home))
    from hermes_cli.plugins import discover_plugins, get_pre_tool_call_directive
    from tools.approval import check_all_command_guards

    discover_plugins(force=True)

    def deny(command, description, **kwargs):
        return "deny"

    ledger_path = Path(home) / "plugin-data" / "scar" / "ledger.json"
    if mode == "gateway":
        Path(dest).write_text(json.dumps(_gateway_forget(Path(home))), encoding="utf-8")
        return 0
    if mode == "ordinary":
        Path(dest).write_text(json.dumps(_ordinary(Path(home), ledger_path, deny)), encoding="utf-8")
        return 0
    if mode == "yolo":
        action, message = get_pre_tool_call_directive(
            "terminal",
            {"command": "rm -rf foo-does-not-exist"},
        )
        plain_action, _plain_message = get_pre_tool_call_directive(
            "terminal",
            {"command": "rm -r other-name"},
        )
        guard = check_all_command_guards(
            "rm -r other-name",
            "local",
            approval_callback=deny,
        )
        payload = {
            "mode": "yolo",
            "approved": bool(guard.get("approved")) if isinstance(guard, dict) else True,
            "action": action,
            "message": message,
            "plain_action": plain_action,
            "scar_count": _scar_count(ledger_path),
            "ledger": ledger_path.read_text(encoding="utf-8") if ledger_path.is_file() else "",
        }
        Path(dest).write_text(json.dumps(payload), encoding="utf-8")
        return 0

    guard = check_all_command_guards(
        "rm -rf foo-does-not-exist",
        "local",
        approval_callback=deny,
    )
    action, message = get_pre_tool_call_directive(
        "terminal",
        {"command": "rm -fr foo-does-not-exist", "timeout": 3},
    )
    plain_action, _plain_message = get_pre_tool_call_directive("terminal", {"command": "ls"})
    read_action, _read_message = get_pre_tool_call_directive(
        "read_file",
        {"path": "notes.txt"},
    )
    shell_action, _shell_message = get_pre_tool_call_directive(
        "terminal",
        {"command": "bash -c 'rm -rf foo-does-not-exist'"},
    )
    sh_action, _sh_message = get_pre_tool_call_directive(
        "terminal",
        {"command": "sh -c 'rm -rf foo-does-not-exist'"},
    )
    env_action, _env_message = get_pre_tool_call_directive(
        "terminal",
        {"command": "env -u PATH rm -rf foo-does-not-exist"},
    )
    echo_action, _echo_message = get_pre_tool_call_directive(
        "terminal",
        {"command": "echo 'bash -c \"rm -rf foo-does-not-exist\"'"},
    )
    other_action, other_message = get_pre_tool_call_directive("marker_tool", {})
    os.environ["HERMES_CRON_SESSION"] = "1"
    cron_action, cron_message = get_pre_tool_call_directive(
        "terminal",
        {"command": "rm -rf foo-does-not-exist"},
    )
    cron_guard = check_all_command_guards(
        "rm -r other-name",
        "local",
        approval_callback=deny,
    )
    payload = {
        "approved": bool(guard.get("approved")) if isinstance(guard, dict) else True,
        "guard_message": guard.get("message") if isinstance(guard, dict) else "",
        "ledger": ledger_path.read_text(encoding="utf-8") if ledger_path.is_file() else "",
        "action": action,
        "message": message,
        "plain_action": plain_action,
        "read_action": read_action,
        "shell_action": shell_action,
        "sh_action": sh_action,
        "env_action": env_action,
        "echo_action": echo_action,
        "other_action": other_action,
        "other_message": other_message,
        "cron_action": cron_action,
        "cron_message": cron_message,
        "cron_approved": bool(cron_guard.get("approved")) if isinstance(cron_guard, dict) else True,
        "cron_scar_count": _scar_count(ledger_path),
    }
    Path(dest).write_text(json.dumps(payload), encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        dest = sys.argv[4] if len(sys.argv) > 4 else ""
        if dest:
            Path(dest).write_text(
                json.dumps({"error": exc.__class__.__name__, "detail": str(exc)}),
                encoding="utf-8",
            )
        raise
