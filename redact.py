"""Remove secret-shaped text before it is written.

The CLI hands the approval hook the raw command, so this plugin cannot rely on
the card's own masking. The patterns below run first and replace each match
whole. Hermes's public redactor then runs with force=True, which ignores
security.redact_secrets: false, for the shapes these patterns do not know.
It keeps only the prefix of a key it knows, such as npm_.
"""

from __future__ import annotations

import re

_URL = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s:@]+:[^/\s@]+@")
_BEARER = re.compile(r"(?i)\b((?:authorization\s*:\s*)?bearer\s+)\S+")
_ENV = re.compile(
    r"(?i)\b([A-Za-z_][A-Za-z0-9_]*(?:TOKEN|SECRET|PASSWORD|PASSWD|API_KEY|ACCESS_KEY|PRIVATE_KEY|CREDENTIAL|_KEY|_PW|_PASS|AUTH))\s*=\s*\S+"
)
_FLAG = re.compile(r"(?i)(--(?:password|token|secret|api[_-]?key)(?:=|\s+))\S+")
_JSON = re.compile(
    r'(?i)("?(?:api[_-]?key|token|password|secret)"?\s*:\s*"?)([^"\s,}]+)'
)
_GITHUB = re.compile(r"\bgh[pousr]_[A-Za-z0-9]{8,}\b")
_GITHUB_PAT = re.compile(r"\bgithub_pat_[A-Za-z0-9_]{8,}\b")
_SLACK = re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{8,}\b")
_PEM = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.DOTALL,
)
_AKIA = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")
_SK = re.compile(r"\b(?:sk|pk)-[A-Za-z0-9_\-]{8,}\b")
_WORD = re.compile(r"(?i)\b(password|secret|token|api[_-]?key)\b(\s*[:=]\s*)(\S+)")
_HF = re.compile(r"\bhf_[A-Za-z0-9]{16,}\b")
_GITLAB = re.compile(r"\bglpat-[A-Za-z0-9_-]{16,}\b")
_GOOGLE = re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")
_SSHPASS = re.compile(r"(?i)(\bsshpass\s+-p\s*)\S+")
_MYSQL = re.compile(r"(?i)(\b(?:mysql|mysqldump|mysqladmin|mariadb)\b[^;&|\n]*?\s(?:-p|--password=))(?=\S)\S+")
_HEX = re.compile(r"\b[A-Fa-f0-9]{32,}\b")
_PATH = re.compile(r"(?:^|[\s\"'])(?:\./|/)[^\s\"']+")


def _hermes(text: str) -> str:
    """The redactor the approval card uses. Absent means skip.

    The admission lint's public list does not name this module. The call is
    the one the card runs, so it is loaded by name instead of a static import.
    """
    try:
        module = __import__("agent.redact", fromlist=["redact_sensitive_text"])
        redact_sensitive_text = module.redact_sensitive_text
    except Exception:
        return text
    try:
        # file_read with secret_file swaps a known key for a sentinel that keeps
        # only its prefix, instead of the head-and-tail mask the card shows.
        out = redact_sensitive_text(
            text, force=True, file_read=True, secret_file=True, redact_url_credentials=True
        )
    except TypeError:
        try:
            out = redact_sensitive_text(text, force=True)
        except Exception:
            return text
    except Exception:
        return text
    return out if isinstance(out, str) else text


def redact(text: str, limit: int = 500) -> str:
    """Return text with secret-shaped spans replaced. The result is capped."""
    if not isinstance(text, str):
        text = str(text)
    cleaned = text.replace("\x00", "")
    cleaned = _URL.sub(r"\1<redacted>:<redacted>@", cleaned)
    cleaned = _BEARER.sub(r"\1<redacted>", cleaned)
    cleaned = _ENV.sub(r"\1=<redacted>", cleaned)
    cleaned = _FLAG.sub(r"\1<redacted>", cleaned)
    cleaned = _JSON.sub(r"\1<redacted>", cleaned)
    cleaned = _GITHUB.sub("<redacted>", cleaned)
    cleaned = _GITHUB_PAT.sub("<redacted>", cleaned)
    cleaned = _SLACK.sub("<redacted>", cleaned)
    cleaned = _PEM.sub("<redacted>", cleaned)
    cleaned = _AKIA.sub("<redacted>", cleaned)
    cleaned = _JWT.sub("<redacted>", cleaned)
    cleaned = _SK.sub("<redacted>", cleaned)
    cleaned = _WORD.sub(r"\1\2<redacted>", cleaned)
    cleaned = _HF.sub("<redacted>", cleaned)
    cleaned = _GITLAB.sub("<redacted>", cleaned)
    cleaned = _GOOGLE.sub("<redacted>", cleaned)
    cleaned = _SSHPASS.sub(r"\1<redacted>", cleaned)
    cleaned = _MYSQL.sub(r"\1<redacted>", cleaned)
    cleaned = _HEX.sub("<redacted>", cleaned)
    cleaned = _hermes(cleaned)
    cleaned = _PATH.sub(" <path>", cleaned)
    cleaned = cleaned.replace("\r", " ").replace("\n", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > limit:
        return cleaned[: limit - 3] + "..."
    return cleaned
