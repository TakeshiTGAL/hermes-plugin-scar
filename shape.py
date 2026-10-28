"""The shape of one tool call.

A scar is the tool name, the argument keys that contained an rm command,
and the danger tokens from that command. The path is not part of the shape.
Echo and the other data commands do not lend their words to the match.
Known wrapper words and up to two other leading words may wrap rm. env options
and assignments are part of that wrapper. A shell -c body is read with the same
rules, including a nested shell. A sentence of words is not a command, so it is
read as "not rm" and never runs out of depth.
"""

from __future__ import annotations

import re
import shlex

MAX_TEXT = 200000
MAX_DEPTH = 8
MAX_STRINGS = 100
TOOL_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
KEY_RE = TOOL_RE
_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

# Words that print or test their arguments. They are not a command prefix.
DATA_COMMANDS = frozenset(
    {
        "echo",
        "printf",
        "cat",
        "head",
        "tail",
        "less",
        "more",
        "grep",
        "egrep",
        "fgrep",
        "sed",
        "awk",
        "wc",
        "tr",
        "sort",
        "uniq",
        "true",
        "false",
        "test",
        "[",
        "cut",
        "rev",
        "od",
        "hexdump",
        "strings",
        "file",
        "stat",
        "date",
        "basename",
        "dirname",
        "read",
        ":",
    }
)
ALLOWED_TOKENS = frozenset({"force", "recursive", "rm"})
_SHELLS = frozenset({"sh", "bash", "dash", "zsh", "ksh", "ash"})
_ENV_SHORT_ARG = frozenset({"u", "C", "P", "S"})
_ENV_LONG_ARG = frozenset(
    {
        "unset",
        "chdir",
        "argv0",
        "split-string",
        "block-signal",
        "ignore-signal",
        "default-signal",
    }
)
MAX_SHELL = 8
# Wrapper words that run the next word as a command. The value is the set of
# flags that take the next word as their value.
_WRAPPERS = {
    "nice": frozenset({"-n"}),
    "nohup": frozenset(),
    "time": frozenset({"-f", "-o"}),
    "timeout": frozenset({"-s", "-k"}),
    "xargs": frozenset({"-n", "-I", "-L", "-P", "-s", "-d", "-E", "-a"}),
    "command": frozenset(),
    "exec": frozenset({"-a"}),
    "builtin": frozenset(),
    "stdbuf": frozenset({"-i", "-o", "-e"}),
    "ionice": frozenset({"-c", "-n", "-p"}),
    "setsid": frozenset(),
    "caffeinate": frozenset({"-t", "-w"}),
    "chronic": frozenset(),
    "doas": frozenset({"-u", "-C"}),
}
# Other leading words peeled before the command ends. Two covers `git rm` and a
# privilege wrapper with a user flag. A sentence of words is not a command.
MAX_GENERIC = 2
# Wrapper steps in one simple command before the shape is refused.
MAX_WRAP = 8


class ShapeError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def command_name(word: str) -> str:
    name = word.replace("\\", "/")
    if len(name) > 1:
        name = name.rstrip("/")
    if "/" in name:
        name = name.rsplit("/", 1)[-1]
    return name


def _is_assignment(word: str) -> bool:
    return _ASSIGN.match(word) is not None


def _split_segments(command: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(command)
    quote = ""
    while i < n:
        ch = command[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < n:
                buf.append(command[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = ""
            i += 1
            continue
        if ch == "\\":
            buf.append(ch)
            if i + 1 < n:
                buf.append(command[i + 1])
                i += 2
            else:
                i += 1
            continue
        if ch in "'\"":
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == "#":
            while i < n and command[i] != "\n":
                i += 1
            continue
        if command.startswith("&&", i) or command.startswith("||", i):
            parts.append("".join(buf))
            buf = []
            i += 2
            continue
        if ch in ";|&\n":
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return parts


def _tokenize(segment: str) -> list[str]:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def _collect_flags(argv: list[str]) -> set[str]:
    tokens = {"rm"}
    for word in argv[1:]:
        if word == "--":
            break
        if word.startswith("--"):
            name = word[2:].split("=", 1)[0]
            if name == "recursive":
                tokens.add("recursive")
            elif name == "force":
                tokens.add("force")
            continue
        if word.startswith("-") and len(word) > 1 and word[1:].isalpha():
            if "r" in word[1:]:
                tokens.add("recursive")
            if "f" in word[1:]:
                tokens.add("force")
    return tokens


def _exec_rms(argv: list[str]) -> set[str]:
    found: set[str] = set()
    for index, word in enumerate(argv):
        if word not in ("-exec", "-execdir"):
            continue
        for later in argv[index + 1 :]:
            if later in (";", "+"):
                break
            if command_name(later) == "rm":
                found |= _collect_flags(argv[argv.index(later, index + 1) :])
                break
    return found


def _shell_script(argv: list[str]) -> str | None:
    """Return the body of a shell -c. None means this argv is not that form."""
    if not argv:
        return None
    name = command_name(argv[0])
    index = 1
    if name == "busybox" and len(argv) > 1 and command_name(argv[1]) in _SHELLS:
        name = command_name(argv[1])
        index = 2
    if name not in _SHELLS:
        return None
    while index < len(argv):
        word = argv[index]
        if word == "--":
            return None
        if word == "-c" or (
            word.startswith("-")
            and not word.startswith("--")
            and len(word) > 1
            and word[1:].isalpha()
            and "c" in word[1:]
        ):
            if index + 1 >= len(argv):
                return None
            return argv[index + 1]
        if word.startswith("-"):
            index += 1
            continue
        return None
    return None


def _command_after_env(argv: list[str]) -> list[str] | None:
    """The command after env's options and assignments. None when argv is not env."""
    if not argv or command_name(argv[0]) != "env":
        return None
    index = 1
    while index < len(argv):
        word = argv[index]
        if _is_assignment(word):
            index += 1
            continue
        if word == "--":
            return argv[index + 1 :]
        if word.startswith("--"):
            name, sep, _value = word[2:].partition("=")
            if sep:
                index += 1
                continue
            if name in _ENV_LONG_ARG:
                index += 2
                continue
            index += 1
            continue
        if word.startswith("-") and len(word) > 1:
            body = word[1:]
            if body[0] in _ENV_SHORT_ARG and len(body) > 1:
                index += 1
                continue
            if len(body) == 1 and body in _ENV_SHORT_ARG:
                index += 2
                continue
            index += 1
            continue
        return argv[index:]
    return []


def _skip_flags(argv: list[str], index: int, takes_value: frozenset[str] = frozenset()) -> int:
    """Skip flags and assignments after a wrapper word. Some flags take the next word."""
    while index < len(argv):
        word = argv[index]
        if _is_assignment(word):
            index += 1
            continue
        if not word.startswith("-") or word == "-":
            break
        if word == "--":
            return index + 1
        index += 2 if word in takes_value else 1
    return index


def _parse_segment(argv: list[str], depth: int) -> set[str]:
    """Read one simple command. Leading wrapper words are peeled in a loop, not by recursion.

    A known wrapper (nice, nohup, timeout, xargs, ...) may repeat. Up to two other
    leading words are peeled as well, so `git rm -rf` and a privilege wrapper with a
    user flag are read. After that, a word that is not rm, a shell -c, or env ends the
    command: it is not the rm shape. Ordinary text therefore never runs out of depth.
    """
    found: set[str] = set()
    generic = 0
    for _step in range(MAX_WRAP + 1):
        while argv and _is_assignment(argv[0]):
            argv = argv[1:]
        if not argv:
            return found
        name = command_name(argv[0])
        if name in DATA_COMMANDS:
            return found
        if name == "rm":
            return found | _collect_flags(argv)
        found |= _exec_rms(argv)
        script = _shell_script(argv)
        if script is not None:
            return found | parse_command(script, depth + 1)
        if name == "env":
            rest = _command_after_env(argv)
            if not rest:
                return found
            argv = rest
            continue
        if name in _WRAPPERS:
            index = _skip_flags(argv, 1, _WRAPPERS[name])
            if name == "timeout" and index < len(argv):
                index += 1
            argv = argv[index:]
            continue
        if generic >= MAX_GENERIC:
            return found
        generic += 1
        argv = argv[_skip_flags(argv, 1):]
    raise ShapeError("depth")


def parse_command(command: str, depth: int = 0) -> set[str]:
    """Return the rm danger tokens in one shell command. The set may be empty."""
    if not isinstance(command, str):
        raise ShapeError("text")
    if len(command) > MAX_TEXT:
        raise ShapeError("text")
    if depth > MAX_SHELL:
        raise ShapeError("depth")
    folded = command.casefold()
    tokens: set[str] = set()
    for segment in _split_segments(folded):
        if segment.strip():
            tokens |= _parse_segment(_tokenize(segment), depth)
    return tokens


def _walk(value: object, depth: int, count: list[int]) -> set[str]:
    if depth > MAX_DEPTH:
        raise ShapeError("depth")
    if isinstance(value, str):
        count[0] += 1
        if count[0] > MAX_STRINGS:
            raise ShapeError("strings")
        return parse_command(value)
    if isinstance(value, dict):
        found: set[str] = set()
        for key, item in value.items():
            if not isinstance(key, str) or KEY_RE.fullmatch(key) is None:
                raise ShapeError("key")
            found |= _walk(item, depth + 1, count)
        return found
    if isinstance(value, list):
        found = set()
        for item in value:
            found |= _walk(item, depth + 1, count)
        return found
    if value is None or isinstance(value, (bool, int, float)):
        return set()
    raise ShapeError("type")


def call_shape(tool: object, args: object, keys: object = None) -> dict:
    """Return tool, contributing argument keys, and sorted danger tokens.

    keys limits the comparison to those argument keys. The hook passes the keys
    a stored scar kept, so other arguments of the call are not read at all.
    """
    if not isinstance(tool, str) or TOOL_RE.fullmatch(tool) is None:
        raise ShapeError("tool")
    if not isinstance(args, dict):
        raise ShapeError("args")
    wanted = None if keys is None else frozenset(keys)
    if wanted is None and len(args) > MAX_STRINGS:
        raise ShapeError("strings")
    found_keys: list[str] = []
    tokens: set[str] = set()
    count = [0]
    for key, value in args.items():
        if wanted is not None and key not in wanted:
            continue
        if not isinstance(key, str) or KEY_RE.fullmatch(key) is None:
            raise ShapeError("key")
        found = _walk(value, 1, count)
        if found:
            found_keys.append(key)
            tokens |= found
    if not tokens <= ALLOWED_TOKENS:
        raise ShapeError("token")
    return {"tool": tool, "arg_keys": sorted(set(found_keys)), "danger_tokens": sorted(tokens)}
