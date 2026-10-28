"""Whether a person can answer this session.

Cron, a single query, and an unattended platform have no card. An isolated
plugin process has no card either. Those sessions do not store a new scar,
and they do not forget one. Hermes checks a permanent allowlist before its
own cron deny, so this module does not treat that deny as the guard.
"""

from __future__ import annotations

import os
import sys

_ON = frozenset({"1", "true", "yes", "on"})
# Same set Hermes uses for approvals.unattended_mode. A person cannot answer.
_UNATTENDED_PLATFORMS = frozenset({"webhook", "msgraph_webhook", "api_server"})


def _on(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _ON


def session_value(name: str) -> str:
    """Session value Hermes reads for this turn, then the process environment.

    A gateway turn binds the platform before the tool call. The public reader
    is ``get_session_env`` on the module Hermes already loaded. This does not
    import that module and does not call a private name. When the reader is
    absent, the process environment is the value.
    """
    module = sys.modules.get("gateway.session_context")
    reader = getattr(module, "get_session_env", None) if module is not None else None
    if callable(reader):
        try:
            return str(reader(name, "") or "")
        except Exception:
            pass
    return os.environ.get(name, "") or ""


def _cron_identity() -> bool:
    """Public cron identity, present from Hermes 0.21.6. Older trees have no module."""
    try:
        from cron.execution_identity import current_cron_execution
    except Exception:
        return False
    try:
        return current_cron_execution() is not None
    except Exception:
        return False


def unattended() -> bool:
    if _on("HERMES_CRON_SESSION") or _on("HERMES_SINGLE_QUERY_SESSION"):
        return True
    platform = session_value("HERMES_SESSION_PLATFORM").strip().lower()
    if platform in _UNATTENDED_PLATFORMS:
        return True
    return _cron_identity()


def in_plugin_host_process() -> bool:
    return bool(os.environ.get("HERMES_PLUGIN_HOST_PROCESS", "").strip())
