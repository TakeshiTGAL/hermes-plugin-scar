"""The plugin clock. The agent does not supply the time."""

from __future__ import annotations

from datetime import datetime

_WEEKDAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


def now_text() -> str:
    """Local time with a numeric offset. Microseconds are dropped."""
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def parse_when(text: str) -> datetime:
    """Parse an aware ISO timestamp. A naive value is refused."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("time")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("time") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("time")
    return parsed


def zone_label(parsed: datetime) -> str:
    offset = parsed.utcoffset()
    if offset is None:
        raise ValueError("time")
    total = int(offset.total_seconds())
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    hours, minutes = divmod(total // 60, 60)
    return f"{sign}{hours:02d}:{minutes:02d}"


def receipt(scar_id: int, recorded_at: str) -> str:
    """Weekday and clock in the stored offset, then the numeric offset."""
    parsed = parse_when(recorded_at)
    weekday = _WEEKDAYS[parsed.weekday()]
    clock = f"{parsed.hour:02d}:{parsed.minute:02d}"
    return f"scar #{scar_id}, {weekday} {clock} {zone_label(parsed)}, you pressed deny"


def receipt_line(scar_id: int, recorded_at: str) -> str:
    return (
        "BLOCKED: "
        + receipt(scar_id, recorded_at)
        + ". Do not paraphrase this command and do not run it again."
    )
