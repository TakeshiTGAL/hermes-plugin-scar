"""Public text matches the tools, and the install notes do not describe training."""

from support import ROOT, schemas

_BANNED = ("mkfs", "sudo", "setprofile", "settrace", "f_back", "tools.approval", "approval_context")
_PINS = (
    "9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031",
    "0.7.0-dev",
    "build 11669",
    "Allow once",
    "Press 4",
    "-t terminal,scar",
    "hermes chat --cli",
    "you pressed deny",
    "_config_version: 50",
    "does not cover the next forget",
)


def test_tool_descriptions_stay_short_and_name_the_job():
    for schema in schemas.ALL_SCHEMAS:
        first = schema["description"].split(". ", 1)[0]
        if not first.endswith("."):
            first += "."
        assert len(first) <= 60
        assert not first.lower().startswith("read-only")
    assert [item["name"] for item in schemas.ALL_SCHEMAS] == ["scar_check", "scar_list", "scar_forget"]


def test_manifest_tools_and_hooks_match_the_code():
    text = (ROOT / "plugin.yaml").read_text(encoding="utf-8")
    assert "provides_tools:\n  - scar_check\n  - scar_list\n  - scar_forget\n" in text
    assert "provides_hooks:\n  - pre_tool_call\n  - post_approval_response\n" in text
    assert 'requires_hermes: ">=0.21.6"' in text
    assert "config_schema" not in text


def test_readme_names_the_card_and_the_pins():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for pin in _PINS:
        assert pin in text
    lowered = text.lower()
    assert "mlx" not in lowered
    assert "scar_train" not in lowered
    assert "advisor" in lowered
    assert "agent-station" in lowered
    assert "hermes-memory-pane" in lowered
    assert "llmslim" in lowered
    assert "model-leaderboard" not in lowered
    assert "scar does not edit files" not in lowered
    assert "scar leaves memory alone" not in lowered
    assert "scar does not compress tool output" not in lowered
    assert "scar:keep-a-scar" in text
    assert "adds one line for that skill to the system prompt skills index" in text
    assert "does not add the skill to the system prompt skills index" not in text
    assert "does not add a line to the system prompt skills index" not in text
    assert "skills toolset is disabled" in text
    assert "15 medium findings" in text
    assert "7 description lines of 63 columns" in text
    assert "is not read as that command, and that call runs" in text
    assert "131,072" in text
    assert "skills index of every session" not in text
    assert "under 2000" not in text


def test_skill_tells_the_agent_to_write_the_command_first():
    text = (ROOT / "skills" / "keep-a-scar" / "SKILL.md").read_text(encoding="utf-8")
    assert "Before the person answers" in text
    assert "Do not invent a recorded time" in text
    assert "rm -rf ./build" in text
    assert "scar:keep-a-scar" in text
    assert "does not cover the next forget" in text
    assert "adds one line for this skill to the system prompt skills index" in text
    assert "does not add a line to the system prompt skills index" not in text
    assert "skills toolset is disabled" in text
    assert "skills index of every session" not in text
    assert "sudo" not in text
    assert "mkfs" not in text


def test_production_source_has_no_scanner_bait():
    for path in ROOT.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for word in _BANNED:
            assert word not in text, f"{path.name}:{word}"


def test_public_files_are_english():
    suffixes = {".py", ".md", ".yaml", ".yml", ".json", ".txt"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        if any(part in {"tests", ".git", "__pycache__"} for part in path.parts):
            continue
        for ch in path.read_text(encoding="utf-8"):
            assert ord(ch) < 0x3000, path.name
