"""Loopback names only. A private LAN address is not this computer."""

from __future__ import annotations

import ipaddress
import unicodedata


def host_is_local(host: object) -> bool:
    """True for localhost, 127.0.0.0/8, and ::1. Nothing else."""
    if not isinstance(host, str) or not host or host != host.strip():
        return False
    if any(ord(ch) < 33 or ch in "@\\%" for ch in host):
        return False
    name = host
    if name.startswith("["):
        if not name.endswith("]") or name.count("[") != 1:
            return False
        name = name[1:-1]
        if not name or "%" in name:
            return False
    folded = unicodedata.normalize("NFC", name).rstrip(".").lower()
    if folded == "localhost":
        return True
    try:
        address = ipaddress.ip_address(name)
    except ValueError:
        return False
    return bool(address.is_loopback)
