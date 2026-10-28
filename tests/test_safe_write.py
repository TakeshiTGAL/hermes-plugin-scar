"""Writes stay inside the chosen folder and do not follow links."""

from __future__ import annotations

import os

import pytest

from safe_write import HARD_LINK_CUT, WriteRefused, write_bytes


def test_a_new_file_is_the_bytes_and_no_temporary_name_remains(tmp_path):
    note = write_bytes(tmp_path, "a.bin", b"RIFF-data", create=True, exclusive=True)
    assert note == ""
    assert (tmp_path / "a.bin").read_bytes() == b"RIFF-data"
    assert list(tmp_path.glob(".rewrite.*")) == []


def test_a_symlink_parent_is_refused_and_the_outside_is_untouched(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "link"
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(WriteRefused) as caught:
        write_bytes(link / "audio", "a.bin", b"RIFF-data", create=True, exclusive=True)
    assert caught.value.kind == "symlink"
    assert list(outside.rglob("*")) == []


def test_a_symlink_at_the_file_is_not_followed(tmp_path):
    target = tmp_path / "target.bin"
    target.write_bytes(b"ORIGINAL")
    dest = tmp_path / "a.bin"
    dest.symlink_to(target)
    with pytest.raises(WriteRefused) as caught:
        write_bytes(tmp_path, "a.bin", b"RIFF-data", create=True, exclusive=True)
    assert caught.value.kind == "symlink"
    assert target.read_bytes() == b"ORIGINAL"
    assert dest.is_symlink()


def test_dotdot_is_refused(tmp_path):
    with pytest.raises(WriteRefused) as caught:
        write_bytes(tmp_path, "../escape.bin", b"RIFF-data", create=True)
    assert caught.value.kind == "outside"
    assert not (tmp_path.parent / "escape.bin").exists()


def test_an_existing_hard_link_can_be_cut_without_changing_the_other_name(tmp_path):
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"ORIGINAL-HARD")
    dest = tmp_path / "a.bin"
    os.link(outside, dest)
    note = write_bytes(tmp_path, "a.bin", b"NEW-BYTES", create=True, exclusive=False, cut_hardlink=True)
    assert note == HARD_LINK_CUT
    assert outside.read_bytes() == b"ORIGINAL-HARD"
    assert dest.read_bytes() == b"NEW-BYTES"
    assert outside.stat().st_ino != dest.stat().st_ino


def test_an_existing_hard_link_can_be_refused(tmp_path):
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"ORIGINAL-HARD")
    dest = tmp_path / "a.bin"
    os.link(outside, dest)
    with pytest.raises(WriteRefused) as caught:
        write_bytes(tmp_path, "a.bin", b"NEW-BYTES", create=True, exclusive=True, cut_hardlink=False)
    assert caught.value.kind == "hardlink"
    assert outside.read_bytes() == b"ORIGINAL-HARD"
    assert dest.stat().st_nlink >= 2
