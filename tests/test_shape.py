"""Command shapes. The path is not the identity. Echo is not a command."""

from support import shape

SAME = {"force", "recursive", "rm"}


def tokens(command: str) -> set[str]:
    return shape.parse_command(command)


def test_rf_spellings_share_one_token_set():
    commands = [
        "rm -rf foo-does-not-exist",
        "rm -fr foo-does-not-exist",
        "rm -r -f foo-does-not-exist",
        "rm -f -r foo-does-not-exist",
        "rm --recursive --force foo-does-not-exist",
        "rm --force --recursive foo-does-not-exist",
        "rm --force=true --recursive foo-does-not-exist",
        "RM -RF foo-does-not-exist",
        "/bin/rm -rf foo-does-not-exist",
        "rm foo-does-not-exist -rf",
        "rm -rf ./other",
        "env FOO=1 rm -rf foo-does-not-exist",
        "env rm -rf foo-does-not-exist",
        "env -i rm -rf foo-does-not-exist",
        "env -u PATH rm -rf foo-does-not-exist",
        "env -uPATH rm -rf foo-does-not-exist",
        "sudo -n rm -rf foo-does-not-exist",
        "bash -c 'rm -rf foo-does-not-exist'",
        'sh -c "rm -rf foo-does-not-exist"',
        "bash -lc 'rm -rf foo-does-not-exist'",
        "env FOO=1 bash -c 'rm -rf foo-does-not-exist'",
        "env -i sh -c 'rm -rf foo-does-not-exist'",
        "bash -c 'sh -c \"rm -rf foo-does-not-exist\"'",
        "find . -exec rm -rf {} +",
        "find . -execdir rm -fr {} +",
        "rm -rf foo-does-not-exist && true",
        "echo hello && rm -rf foo-does-not-exist",
        "git rm -rf foo-does-not-exist",
        "rm -rf foo-does-not-exist # a note",
    ]
    for command in commands:
        assert tokens(command) == SAME, command


def test_echo_and_plain_commands_have_no_tokens():
    assert tokens("echo rm -rf is dangerous") == set()
    assert tokens('echo "rm -rf foo-does-not-exist"') == set()
    assert tokens("FOO=1 echo rm -rf foo-does-not-exist") == set()
    assert tokens("ls") == set()
    assert tokens("rm -r foo-does-not-exist") == {"recursive", "rm"}
    assert tokens("rm -- -rf foo-does-not-exist") == {"rm"}


def test_a_data_command_and_other_interpreters_are_not_the_shape():
    assert tokens("echo 'bash -c \"rm -rf foo-does-not-exist\"'") == set()
    assert tokens("bash -c 'echo rm -rf foo-does-not-exist'") == set()
    assert tokens("bash -c 'ls'") == set()
    assert tokens("python -c 'import os; os.system(\"rm -rf foo-does-not-exist\")'") == set()
    assert tokens("node -e 'require(\"fs\").rmSync(\"foo-does-not-exist\")'") == set()
    assert tokens("bash ./script.sh") == set()


def test_shell_nesting_past_the_cap_is_refused():
    import shlex

    import pytest

    inner = "rm -rf foo-does-not-exist"
    for _ in range(3):
        inner = "bash -c " + shlex.quote(inner)
    assert tokens(inner) == SAME
    deep = "rm -rf foo-does-not-exist"
    for _ in range(shape.MAX_SHELL + 2):
        deep = "bash -c " + shlex.quote(deep)
    with pytest.raises(shape.ShapeError):
        shape.parse_command(deep)


def test_extra_keys_do_not_change_the_contributing_keys():
    left = shape.call_shape("terminal", {"command": "rm -rf foo-does-not-exist"})
    right = shape.call_shape(
        "terminal",
        {
            "command": "rm -fr foo-does-not-exist",
            "timeout": 5,
            "background": False,
            "workdir": "/tmp/build",
            "pty": True,
            "notify": False,
        },
    )
    assert left["arg_keys"] == ["command"]
    assert right["arg_keys"] == ["command"]
    assert left["danger_tokens"] == right["danger_tokens"] == ["force", "recursive", "rm"]


def test_limits_refuse_a_shape_that_cannot_be_compared():
    import pytest

    with pytest.raises(shape.ShapeError):
        shape.call_shape("terminal", "ls")
    with pytest.raises(shape.ShapeError):
        shape.call_shape("terminal", {"command": "x" * (shape.MAX_TEXT + 1)})
    nested: object = "rm -rf foo-does-not-exist"
    for _ in range(shape.MAX_DEPTH + 1):
        nested = {"inner": nested}
    with pytest.raises(shape.ShapeError):
        shape.call_shape("terminal", nested)
    with pytest.raises(shape.ShapeError):
        shape.call_shape("terminal", {"n": ["a"] * (shape.MAX_STRINGS + 1)})


def test_sentences_and_long_argument_lists_are_not_rm_and_do_not_run_out_of_depth():
    sentence = "The build finished and all the tests passed on the main branch today."
    assert tokens(sentence) == set()
    assert tokens(" ".join(["word"] * 100)) == set()
    assert tokens(" ".join(["word"] * 1000)) == set()
    assert tokens("touch a.txt b.txt c.txt d.txt e.txt f.txt g.txt h.txt i.txt") == set()
    assert tokens("git add a.py b.py c.py d.py e.py f.py g.py h.py") == set()
    assert tokens("make -j4 all check install docs lint test dist clean") == set()
    assert tokens("x" * shape.MAX_TEXT) == set()


def test_wrappers_are_peeled_in_a_loop():
    for command in (
        "sudo -u root rm -rf foo-does-not-exist",
        "git -C repo rm -rf foo-does-not-exist",
        "timeout 5 rm -rf foo-does-not-exist",
        "timeout -s KILL 5 rm -rf foo-does-not-exist",
        "nice -n 5 nohup rm -rf foo-does-not-exist",
        "xargs -n 1 rm -rf",
        "time nice nohup timeout 5 rm -rf foo-does-not-exist",
        "env FOO=1 nice rm -rf foo-does-not-exist",
    ):
        assert tokens(command) == SAME, command
    assert tokens("touch a.txt rm-notes.txt") == set()
    assert tokens("nice echo rm -rf foo-does-not-exist") == set()


def test_a_wrapper_chain_past_the_cap_is_refused():
    import pytest

    with pytest.raises(shape.ShapeError):
        shape.parse_command("nice " * (shape.MAX_WRAP + 1) + "rm -rf foo-does-not-exist")


def test_keys_limit_what_is_read():
    out = shape.call_shape(
        "terminal",
        {"command": "ls", "note": "rm -rf foo-does-not-exist", "stdin": "y" * (shape.MAX_TEXT + 1)},
        keys={"command"},
    )
    assert out["danger_tokens"] == []
    assert out["arg_keys"] == []
