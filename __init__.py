"""Keep a denied command shape and stop that shape before it runs again."""

from pathlib import Path

from . import hooks, schemas, tools
from .version import __version__  # noqa: F401

_SKILL = Path(__file__).resolve().parent / "skills" / "keep-a-scar" / "SKILL.md"
_SKILL_TEXT = (
    "Stop a command you denied once when that same shape comes back. "
    "Use scar_check or scar_list."
)


def register(ctx) -> None:
    for schema in schemas.ALL_SCHEMAS:
        ctx.register_tool(
            name=schema["name"],
            toolset="scar",
            schema=schema,
            handler=tools.HANDLERS[schema["name"]],
        )
    ctx.register_skill("keep-a-scar", _SKILL, description=_SKILL_TEXT)
    ctx.register_hook("pre_tool_call", hooks.on_pre_tool_call)
    ctx.register_hook("post_approval_response", hooks.on_post_approval_response)
